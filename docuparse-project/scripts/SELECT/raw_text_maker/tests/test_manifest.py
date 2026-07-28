"""Manifesto de formatados: dedup, persistência e regra de pendência."""

from pathlib import Path

from raw_text_maker.manifest import FormattedManifest, is_pending


def _txt(path: Path, conteudo: str = "texto") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(conteudo, encoding="utf-8")
    return path


def test_mark_dedups_within_a_run(tmp_path):
    with FormattedManifest(tmp_path / "m.csv") as m:
        assert m.mark("Água/a.pdf", "docling", 10) is True
        assert m.mark("Água/a.pdf", "docling", 10) is False  # já registrado
        assert len(m) == 1


def test_manifest_accumulates_across_runs(tmp_path):
    path = tmp_path / "m.csv"
    with FormattedManifest(path) as m:
        m.mark("Água/a.pdf", "docling", 10)
    with FormattedManifest(path) as m:
        assert m.already_formatted("Água/a.pdf")  # sobreviveu ao fechamento
        m.mark("Energia/b.pdf", "docling", 20)
    with FormattedManifest(path) as m:
        assert len(m) == 2


def test_header_written_once(tmp_path):
    path = tmp_path / "m.csv"
    for rel in ("a.pdf", "b.pdf"):
        with FormattedManifest(path) as m:
            m.mark(rel, "docling", 1)
    linhas = path.read_text(encoding="utf-8").strip().splitlines()
    assert linhas[0].startswith("arquivo_origem")
    assert len(linhas) == 3  # cabeçalho + 2 registros


# --- is_pending: o gate propriamente dito -----------------------------------


def test_pending_when_not_in_manifest(tmp_path):
    dest = _txt(tmp_path / "a.txt")
    with FormattedManifest(tmp_path / "m.csv") as m:
        assert is_pending(m, "a.pdf", dest) is True


def test_not_pending_when_marked_and_txt_present(tmp_path):
    dest = _txt(tmp_path / "a.txt")
    with FormattedManifest(tmp_path / "m.csv") as m:
        m.mark("a.pdf", "docling", 5)
        assert is_pending(m, "a.pdf", dest) is False


def test_pending_again_when_txt_was_deleted(tmp_path):
    dest = _txt(tmp_path / "a.txt")
    with FormattedManifest(tmp_path / "m.csv") as m:
        m.mark("a.pdf", "docling", 5)
        dest.unlink()
        # O registro sozinho daria o documento por pronto para sempre.
        assert is_pending(m, "a.pdf", dest) is True


def test_pending_again_when_txt_is_empty(tmp_path):
    dest = _txt(tmp_path / "a.txt", conteudo="")
    with FormattedManifest(tmp_path / "m.csv") as m:
        m.mark("a.pdf", "docling", 5)
        assert is_pending(m, "a.pdf", dest) is True
