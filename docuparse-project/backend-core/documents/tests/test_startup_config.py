"""Log de configuração no boot (documents/startup.py)."""

from __future__ import annotations

from django.test import SimpleTestCase

from documents.startup import log_startup_config


class InternalTokenStartupWarningTests(SimpleTestCase):
    """AR-02: o token interno ausente fora de dev precisa aparecer no log do boot."""

    def test_logs_error_when_token_missing_outside_dev(self) -> None:
        with self.settings(
            DOCUPARSE_INTERNAL_SERVICE_TOKEN="",
            INTERNAL_ENDPOINTS_OPEN_WITHOUT_TOKEN=False,
            DEPLOYMENT_ENVIRONMENT="",
        ):
            with self.assertLogs("documents.startup", level="ERROR") as logs:
                log_startup_config()
        assert any("DOCUPARSE_INTERNAL_SERVICE_TOKEN ausente" in m for m in logs.output)

    def test_no_error_when_token_missing_in_dev(self) -> None:
        with self.settings(
            DOCUPARSE_INTERNAL_SERVICE_TOKEN="",
            INTERNAL_ENDPOINTS_OPEN_WITHOUT_TOKEN=True,
        ):
            with self.assertNoLogs("documents.startup", level="ERROR"):
                log_startup_config()

    def test_no_error_when_token_configured(self) -> None:
        with self.settings(
            DOCUPARSE_INTERNAL_SERVICE_TOKEN="secret",
            INTERNAL_ENDPOINTS_OPEN_WITHOUT_TOKEN=False,
        ):
            with self.assertNoLogs("documents.startup", level="ERROR"):
                log_startup_config()
