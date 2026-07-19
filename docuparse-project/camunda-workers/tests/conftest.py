"""Shared pytest fixtures for camunda-workers unit tests.

All worker tests must run offline: `httpx.AsyncClient` calls to backend-core,
layout-service, and langextract-service are intercepted via `respx` rather than
hitting real network endpoints (constitution: unit tests MUST NOT make network calls).
"""
import sys
from pathlib import Path

import pytest
import respx

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import settings  # noqa: E402


@pytest.fixture
def mock_core_api():
    """Intercept httpx calls to backend-core (settings.backend_core_url)."""
    with respx.mock(base_url=settings.backend_core_url, assert_all_called=False) as router:
        yield router


@pytest.fixture
def mock_layout_api():
    """Intercept httpx calls to layout-service (settings.layout_service_url)."""
    with respx.mock(base_url=settings.layout_service_url, assert_all_called=False) as router:
        yield router


@pytest.fixture
def mock_langextract_api():
    """Intercept httpx calls to langextract-service (settings.langextract_service_url)."""
    with respx.mock(base_url=settings.langextract_service_url, assert_all_called=False) as router:
        yield router
