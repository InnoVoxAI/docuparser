"""Modo --formatted: o gate impede reenviar ao backend o que já foi formatado.

A sonda de camada de texto e o ``ensure_available`` são substituídos: o que está
sob teste é a **decisão** de enviar ou não, não o PyMuPDF.
"""

from pathlib import Path

import pytest
from raw_text_maker import pipeline as pipeline_mod
from raw_text_maker.config import build_config
from raw_text_maker.manifest import FormattedManifest
from raw_text_maker.ocr_client import OcrOutcome
from raw_text_maker.pipeline import run, seed_formatted_manifest

_COM_TEXTO = "digital.pdf"
_SCAN = "scan.pdf"


@pytest.fixture
def arvore(tmp_path):
    """Duas categorias: um PDF com camada de texto e um scan."""
    src = tmp_path / "downloads"
    (src / "Água").mkdir(parents=True)
    (src / "Água" / _COM_TEXTO).write_bytes(b"%PDF-1.7 digital")
    (src / "Energia").mkdir(parents=True)
    (src / "Energia" / _SCAN).write_bytes(b"%PDF-1.7 scan")
    return src


@pytest.fixture(autouse=True)
def _sem_pymupdf(monkeypatch):
    """Sonda determinística: só ``digital.pdf`` tem camada de texto."""
    monkeypatch.setattr(pipeline_mod, "ensure_available", lambda: None)
    monkeypatch.setattr(
        pipeline_mod, "has_text_layer", lambda source, _min: source.name == _COM_TEXTO
    )


class RecordingOcr:
    """Substitui ``extract_raw_text`` e registra o que foi enviado."""

    def __init__(self, engine="docling", formatted="  col1   col2  "):
        self.enviados: list[str] = []
        self.engine = engine
        self.formatted = formatted

    def __call__(self, source: Path, config, *, session=None, sleep=None):  # noqa: ANN001
        self.enviados.append(source.name)
        return OcrOutcome(
            ok=True,
            raw_text="texto",
            raw_text_formatted=self.formatted,
            engine=self.engine,
            tentativas=1,
        )


def _config(src, **kwargs):
    return build_config(src, formatted=True, **kwargs)


def _preparar_txts(config, *nomes):
    """Cria os .txt como se o modo padrão já tivesse rodado."""
    for rel in nomes:
        dest = (config.output_root / rel).with_suffix(".txt")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("texto padrão", encoding="utf-8")


def test_first_formatted_run_sends_only_text_layer_docs(arvore, monkeypatch):
    config = _config(arvore)
    _preparar_txts(config, f"Água/{_COM_TEXTO}", f"Energia/{_SCAN}")
    ocr = RecordingOcr()
    monkeypatch.setattr(pipeline_mod, "extract_raw_text", ocr)
    monkeypatch.setattr(pipeline_mod, "check_service", lambda c, session=None: ["docling"])

    summary = run(config, session=object())

    assert ocr.enviados == [_COM_TEXTO]  # o scan não é reenviado
    assert summary["formatados"] == 1
    assert summary["mantidos_scan"] == 1


def test_second_run_does_not_resend_already_formatted(arvore, monkeypatch):
    config = _config(arvore)
    _preparar_txts(config, f"Água/{_COM_TEXTO}", f"Energia/{_SCAN}")
    monkeypatch.setattr(pipeline_mod, "check_service", lambda c, session=None: ["docling"])

    primeiro = RecordingOcr()
    monkeypatch.setattr(pipeline_mod, "extract_raw_text", primeiro)
    run(config, session=object())
    assert primeiro.enviados == [_COM_TEXTO]

    # Segunda run: nada mudou na árvore → nada deve ir ao backend.
    segundo = RecordingOcr()
    monkeypatch.setattr(pipeline_mod, "extract_raw_text", segundo)
    summary = run(config, session=object())

    assert segundo.enviados == []
    assert summary["ja_formatados"] == 1
    assert summary["formatados"] == 0


def test_new_document_is_formatted_without_touching_the_old_ones(arvore, monkeypatch):
    config = _config(arvore)
    _preparar_txts(config, f"Água/{_COM_TEXTO}", f"Energia/{_SCAN}")
    monkeypatch.setattr(pipeline_mod, "check_service", lambda c, session=None: ["docling"])
    monkeypatch.setattr(pipeline_mod, "extract_raw_text", RecordingOcr())
    run(config, session=object())

    # Chega uma remessa nova com camada de texto.
    novo = arvore / "Água" / _COM_TEXTO.replace("digital", "digital2")
    novo.write_bytes(b"%PDF-1.7 digital")
    monkeypatch.setattr(
        pipeline_mod, "has_text_layer", lambda source, _min: source.name.startswith("digital")
    )
    _preparar_txts(config, f"Água/{novo.name}")

    ocr = RecordingOcr()
    monkeypatch.setattr(pipeline_mod, "extract_raw_text", ocr)
    summary = run(config, session=object())

    assert ocr.enviados == [novo.name]  # só o novo
    assert summary["formatados"] == 1
    assert summary["ja_formatados"] == 1


def test_reformat_all_ignores_the_manifest(arvore, monkeypatch):
    config = _config(arvore)
    _preparar_txts(config, f"Água/{_COM_TEXTO}", f"Energia/{_SCAN}")
    monkeypatch.setattr(pipeline_mod, "check_service", lambda c, session=None: ["docling"])
    monkeypatch.setattr(pipeline_mod, "extract_raw_text", RecordingOcr())
    run(config, session=object())

    forcado = _config(arvore, reformat_all=True)
    ocr = RecordingOcr()
    monkeypatch.setattr(pipeline_mod, "extract_raw_text", ocr)
    run(forcado, session=object())

    assert ocr.enviados == [_COM_TEXTO]  # reenviado apesar do manifesto


def test_non_docling_result_is_not_recorded_as_formatted(arvore, monkeypatch):
    """Se o backend não confirmar docling, o .txt é preservado e nada é marcado —
    senão o documento nunca mais seria tentado."""
    config = _config(arvore)
    _preparar_txts(config, f"Água/{_COM_TEXTO}", f"Energia/{_SCAN}")
    monkeypatch.setattr(pipeline_mod, "check_service", lambda c, session=None: ["docling"])
    monkeypatch.setattr(
        pipeline_mod, "extract_raw_text", RecordingOcr(engine="openrouter", formatted="")
    )

    summary = run(config, session=object())

    assert summary["sem_formatado"] == 1
    assert summary["formatados"] == 0
    with FormattedManifest(config.manifest_path) as m:
        assert not m.already_formatted(f"Água/{_COM_TEXTO}")


# --- semeadura ---------------------------------------------------------------


def test_seed_marks_only_text_layer_docs_that_have_a_txt(arvore):
    config = _config(arvore)
    _preparar_txts(config, f"Água/{_COM_TEXTO}", f"Energia/{_SCAN}")

    summary = seed_formatted_manifest(config)

    assert summary["semeados"] == 1  # só o digital
    assert summary["ignorados"] == 1  # o scan
    with FormattedManifest(config.manifest_path) as m:
        assert m.already_formatted(f"Água/{_COM_TEXTO}")
        assert not m.already_formatted(f"Energia/{_SCAN}")


def test_seeded_tree_sends_nothing_on_the_next_formatted_run(arvore, monkeypatch):
    """O ponto da semeadura: migrar uma árvore já formatada sem reprocessá-la."""
    config = _config(arvore)
    _preparar_txts(config, f"Água/{_COM_TEXTO}", f"Energia/{_SCAN}")
    seed_formatted_manifest(config)

    ocr = RecordingOcr()
    monkeypatch.setattr(pipeline_mod, "extract_raw_text", ocr)
    monkeypatch.setattr(pipeline_mod, "check_service", lambda c, session=None: ["docling"])
    summary = run(config, session=object())

    assert ocr.enviados == []
    assert summary["ja_formatados"] == 1


def test_seed_skips_documents_without_txt(arvore):
    config = _config(arvore)
    _preparar_txts(config, f"Energia/{_SCAN}")  # o digital ainda não tem .txt

    summary = seed_formatted_manifest(config)

    assert summary["semeados"] == 0
    assert summary["ignorados"] == 2
