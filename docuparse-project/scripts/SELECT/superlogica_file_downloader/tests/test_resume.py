"""Retomada idempotente + fail-soft de ponta a ponta (RN-4/RN-6/E-12)."""

import csv

from superlogica_file_downloader.config import build_config
from superlogica_file_downloader.map_io import MAP_COLUMNS, load_map
from superlogica_file_downloader.pipeline import run

_PDF = b"%PDF-1.7\ncorpo\n"
_JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"\x00" * 20
_URL_OK = "https://x/publico/downloadarquivo?id=1&hash=h"
_URL_BAD = "https://x/publico/downloadarquivo?id=2&hash=h"
_URL_IMG = "https://x/publico/downloadarquivo?id=3&hash=h"


class FakeResponse:
    def __init__(self, status_code, content=b"", headers=None):
        self.status_code = status_code
        self.content = content
        self.headers = headers or {}


class RoutingSession:
    """Responde por URL e registra as chamadas."""

    def __init__(self):
        self.calls: list[str] = []

    def get(self, url, timeout=None, stream=False):  # noqa: ANN001
        self.calls.append(url)
        if url == _URL_OK:
            return FakeResponse(200, _PDF, {"Content-Type": "application/pdf"})
        return FakeResponse(404)


def _noop(_seconds):
    pass


def _write_map(path):
    rows = [
        {"url_download": _URL_OK, "nome_arquivo": "a.pdf", "pasta_destino": "Água",
         "categoria_bruta": "Água", "hyperlink_origem": "https://x/arquivos?accesskey=k",
         "pdf_origem": "d.pdf", "status": "pendente", "fornecedor": "F", "complemento": ""},
        {"url_download": _URL_BAD, "nome_arquivo": "b.pdf", "pasta_destino": "Água",
         "categoria_bruta": "Água", "hyperlink_origem": "https://x/arquivos?accesskey=k",
         "pdf_origem": "d.pdf", "status": "pendente", "fornecedor": "F", "complemento": ""},
    ]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=MAP_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({c: row.get(c, "") for c in MAP_COLUMNS})


def _read(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def test_first_run_downloads_ok_and_records_error(tmp_path):
    config = build_config(tmp_path)
    _write_map(config.map_path)
    session = RoutingSession()

    summary = run(config, session=session, sleep=_noop)

    assert summary["baixados"] == 1
    assert summary["erros"] == 1
    assert (config.downloads_root / "Água" / "a.pdf").exists()
    assert not (config.downloads_root / "Água" / "b.pdf").exists()

    final = _read(config.final_csv_path)
    assert [r["nome_arquivo"] for r in final] == ["a.pdf"]

    statuses = {r.url_download: r.status for r in load_map(config.map_path)}
    assert statuses[_URL_OK] == "baixado"
    assert statuses[_URL_BAD] == "erro"


def test_rerun_skips_done_and_retries_error_without_duplicating(tmp_path):
    config = build_config(tmp_path)
    _write_map(config.map_path)
    run(config, session=RoutingSession(), sleep=_noop)

    # Reexecução: a linha concluída não é rebaixada; a que falhou é re-tentada.
    session2 = RoutingSession()
    summary2 = run(config, session=session2, sleep=_noop)

    assert _URL_OK not in session2.calls  # pulada (status baixado + arquivo presente)
    assert _URL_BAD in session2.calls      # re-tentada
    assert summary2["pulados"] == 1

    final = _read(config.final_csv_path)
    assert [r["nome_arquivo"] for r in final] == ["a.pdf"]  # sem duplicata (RN-6)


class ExpiredSession:
    """Sempre responde 403 (accesskey expirado)."""

    def get(self, url, timeout=None, stream=False):  # noqa: ANN001
        return FakeResponse(403)


def test_expiration_is_flagged_in_summary_and_error_report(tmp_path):
    config = build_config(tmp_path)
    _write_map(config.map_path)

    summary = run(config, session=ExpiredSession(), sleep=_noop)

    assert summary["expiracao"] >= 1  # sinal E-04 no resumo
    erros = _read(config.errors_path)
    assert any(r["possivel_expiracao"] == "sim" for r in erros)


def test_rerun_redownloads_when_file_missing(tmp_path):
    config = build_config(tmp_path)
    _write_map(config.map_path)
    run(config, session=RoutingSession(), sleep=_noop)

    # status=baixado mas o arquivo sumiu do disco → deve rebaixar.
    (config.downloads_root / "Água" / "a.pdf").unlink()
    session2 = RoutingSession()
    run(config, session=session2, sleep=_noop)

    assert _URL_OK in session2.calls
    assert (config.downloads_root / "Água" / "a.pdf").exists()


# --- Colisão superveniente: remessa nova com arquivo homônimo ---------------

_URL_NOVO = "https://x/publico/downloadarquivo?id=3&hash=h"


class AlwaysOkSession:
    """Entrega PDF para qualquer URL e registra as chamadas."""

    def __init__(self):
        self.calls: list[str] = []

    def get(self, url, timeout=None, stream=False):  # noqa: ANN001
        self.calls.append(url)
        return FakeResponse(200, _PDF, {"Content-Type": "application/pdf"})


def _append_colliding_row(path):
    """Acrescenta ao mapa uma linha nova com o MESMO nome/pasta de 'a.pdf'."""
    rows = _read(path)
    rows.append({
        "url_download": _URL_NOVO, "nome_arquivo": "a.pdf", "pasta_destino": "Água",
        "categoria_bruta": "Água", "hyperlink_origem": "https://x/arquivos?accesskey=k2",
        "pdf_origem": "remessa2.pdf", "status": "pendente", "fornecedor": "F",
        "complemento": "",
    })
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=MAP_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({c: row.get(c, "") for c in MAP_COLUMNS})


def test_new_homonym_does_not_redownload_the_already_saved_file(tmp_path):
    """Regressão: a colisão que só aparece na 2ª remessa mudava o nome calculado
    de uma linha já baixada, e a Fase B a rebaixava (arquivo órfão + duplicata)."""
    config = build_config(tmp_path)
    _write_map(config.map_path)
    run(config, session=AlwaysOkSession(), sleep=_noop)
    assert (config.downloads_root / "Água" / "a.pdf").exists()

    _append_colliding_row(config.map_path)
    session2 = AlwaysOkSession()
    summary = run(config, session=session2, sleep=_noop)

    # A linha antiga não é rebaixada, mesmo com o nome calculado agora prefixado.
    assert _URL_OK not in session2.calls
    assert _URL_NOVO in session2.calls

    # O arquivo antigo fica onde está; o novo entra com o prefixo determinístico.
    assert (config.downloads_root / "Água" / "a.pdf").exists()
    assert (config.downloads_root / "Água" / "3_a.pdf").exists()
    assert not (config.downloads_root / "Água" / "1_a.pdf").exists()  # sem órfão

    # E o CSV final ganha exatamente uma linha nova (sem duplicar a antiga).
    final = _read(config.final_csv_path)
    caminhos = [r["caminho_local"] for r in final]
    assert len(caminhos) == len(set(caminhos))
    assert sum("a.pdf" in c for c in caminhos) == 2
    assert summary["pulados"] == 2  # a.pdf e b.pdf (ambas baixadas na 1ª run)
    assert summary["baixados"] == 1  # só a linha nova


# --- Comprovantes em imagem (não-PDF) ---------------------------------------


def _write_single(path, nome, url=_URL_IMG):
    row = {
        "url_download": url, "nome_arquivo": nome, "pasta_destino": "Administração",
        "categoria_bruta": "Administração", "hyperlink_origem": "https://x/arquivos?accesskey=k",
        "pdf_origem": "d.pdf", "status": "pendente", "fornecedor": "F", "complemento": "",
    }
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=MAP_COLUMNS)
        writer.writeheader()
        writer.writerow({c: row.get(c, "") for c in MAP_COLUMNS})


class ImgSession:
    def get(self, url, timeout=None, stream=False):  # noqa: ANN001
        return FakeResponse(200, _JPEG, {"Content-Type": "image/jpeg"})


def test_image_comprovante_is_downloaded_and_named_with_real_extension(tmp_path):
    """Um comprovante .jpg passa pela validação, é salvo com a extensão real e
    entra no CSV final — sem virar erro 'assinatura não reconhecida'."""
    config = build_config(tmp_path)
    _write_single(config.map_path, "comprovante_21-07-2026.jpg")

    summary = run(config, session=ImgSession(), sleep=_noop)

    assert summary["baixados"] == 1
    assert summary["erros"] == 0
    dest = config.downloads_root / "Administração" / "comprovante_21-07-2026.jpg"
    assert dest.exists()  # extensão real preservada (não .jpg.pdf)
    assert dest.read_bytes() == _JPEG
    final = _read(config.final_csv_path)
    assert final[0]["nome_arquivo"] == "comprovante_21-07-2026.jpg"


def test_pdf_only_rejects_image_comprovante(tmp_path):
    """Com --pdf-only (accept_images=False), a imagem volta a ser rejeitada."""
    config = build_config(tmp_path, accept_images=False)
    _write_single(config.map_path, "comprovante.jpg")

    summary = run(config, session=ImgSession(), sleep=_noop)

    assert summary["erros"] == 1
    assert summary["baixados"] == 0
