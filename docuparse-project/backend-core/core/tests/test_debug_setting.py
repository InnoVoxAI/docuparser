"""AR-03: DEBUG precisa ser lido como booleano, com padrão desligado."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest
from core.env import env_flag

BACKEND_CORE_DIR = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("raw", ["False", "false", "0", "no", "off", "", " ", "x"])
def test_env_flag_false_values(raw: str) -> None:
    with mock.patch.dict(os.environ, {"AR03_FLAG": raw}):
        assert env_flag("AR03_FLAG") is False


@pytest.mark.parametrize("raw", ["True", "true", "1", "yes", "on", " TRUE "])
def test_env_flag_true_values(raw: str) -> None:
    with mock.patch.dict(os.environ, {"AR03_FLAG": raw}):
        assert env_flag("AR03_FLAG") is True


def test_env_flag_missing_uses_default() -> None:
    with mock.patch.dict(os.environ):
        os.environ.pop("AR03_FLAG", None)
        assert env_flag("AR03_FLAG") is False
        assert env_flag("AR03_FLAG", default=True) is True


def _settings_debug(debug_value: str | None) -> str:
    """Importa core.settings num processo limpo e devolve repr(DEBUG)."""
    env = {**os.environ, "USE_TELEMETRY": "false"}
    env.pop("DEBUG", None)
    if debug_value is not None:
        env["DEBUG"] = debug_value
    result = subprocess.run(
        [sys.executable, "-c", "import core.settings as s; print(repr(s.DEBUG))"],
        cwd=BACKEND_CORE_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip().splitlines()[-1]


@pytest.mark.parametrize(
    ("debug_value", "expected"),
    [("False", "False"), ("True", "True"), (None, "False")],
)
def test_settings_debug_parses_env(debug_value: str | None, expected: str) -> None:
    assert _settings_debug(debug_value) == expected
