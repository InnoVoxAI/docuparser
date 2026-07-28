"""Gravação atômica: promoção via rename e limpeza do .part em falha (E-11)."""

import os

import pytest
from superlogica_file_downloader.atomic import save_atomic

_PDF = b"%PDF-1.7\ncorpo\n"


def test_save_atomic_creates_final_file_and_dirs(tmp_path):
    dest = tmp_path / "downloads" / "Água" / "a.pdf"
    save_atomic(dest, _PDF)
    assert dest.exists()
    assert dest.read_bytes() == _PDF
    # nenhum arquivo temporário deixado para trás
    assert not dest.with_name(dest.name + ".part").exists()


def test_failure_during_replace_leaves_no_final_and_cleans_part(tmp_path, monkeypatch):
    dest = tmp_path / "a.pdf"

    def _boom(src, dst):  # noqa: ANN001
        raise OSError("falha simulada no rename")

    monkeypatch.setattr(os, "replace", _boom)
    with pytest.raises(OSError):
        save_atomic(dest, _PDF)

    # nada com o nome final; o .part foi removido (E-11)
    assert not dest.exists()
    assert not dest.with_name(dest.name + ".part").exists()
