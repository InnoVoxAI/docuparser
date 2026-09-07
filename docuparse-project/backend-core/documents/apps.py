from django.apps import AppConfig


class DocumentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "documents"

    def ready(self) -> None:
        # Registra os receivers de sinal (limpeza de objetos de storage no delete).
        from documents import signals  # noqa: F401
        from documents.startup import log_startup_config

        log_startup_config()
