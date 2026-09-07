"""SC-007 (spec 018): o provisionamento por-tenant e a rotina de startup
engolida por `except` foram REMOVIDOS, não desativados."""

from __future__ import annotations

from pathlib import Path

_BACKEND_CORE = Path(__file__).resolve().parents[2]


def _read(relpath: str) -> str:
    return (_BACKEND_CORE / relpath).read_text(encoding="utf-8")


def test_startup_has_no_ensure_default_schemas() -> None:
    assert "ensure_default_schemas" not in _read("documents/startup.py")


def test_documents_apps_has_no_silent_seed_block() -> None:
    source = _read("documents/apps.py")
    assert "ensure_default_schemas" not in source
    assert "except Exception:" not in source


def test_seed_data_has_no_per_tenant_schema_loop() -> None:
    source = _read("users/management/commands/seed_data.py")
    assert "schema_context" not in source
    assert "DEFAULT_SCHEMAS" not in source
    assert "seed_default_catalog" in source
