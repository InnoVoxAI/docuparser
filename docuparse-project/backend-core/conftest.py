from __future__ import annotations

import os

import django
import pytest


def pytest_configure(config: pytest.Config) -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
    django.setup()


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Skip tests marked 'tenant_db' when PostgreSQL is not available."""
    if os.environ.get("POSTGRES_HOST"):
        return
    skip_marker = pytest.mark.skip(
        reason="tenant_db tests require POSTGRES_HOST env var (PostgreSQL only)"
    )
    for item in items:
        if item.get_closest_marker("tenant_db"):
            item.add_marker(skip_marker)


def pytest_configure_markers(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "tenant_db: marks tests that require a real PostgreSQL database with schema support",
    )
