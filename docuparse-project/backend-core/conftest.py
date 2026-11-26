from __future__ import annotations

import os

import django
import pytest


def pytest_configure(config: pytest.Config) -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
    django.setup()

    # O relógio do dev container (WSL2) chega a voltar alguns segundos quando a
    # hora é ressincronizada. Um JWT emitido no setUp fica então com `iat` "no
    # futuro" e o PyJWT o recusa (ImmatureSignatureError), o que aparece como um
    # 401 aleatório em qualquer teste de API. A tolerância cobre esse salto. O
    # backend de tokens é montado uma vez na importação, por isso
    # `override_settings(SIMPLE_JWT=...)` não o alcança.
    from rest_framework_simplejwt.state import token_backend

    token_backend.leeway = 30


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


@pytest.fixture(autouse=True)
def _reset_tenant_schema():
    """JWTTenantMiddleware calls connection.set_tenant(...) to switch the
    session's search_path for tenant-scoped requests. Django's test runner
    reuses the same connection across every test method (only the
    transaction/savepoint is rolled back), so without this the schema switch
    from one authenticated test leaks into every test that runs after it.
    """
    from django.db import connection

    connection.set_schema_to_public()
    yield
    connection.set_schema_to_public()
