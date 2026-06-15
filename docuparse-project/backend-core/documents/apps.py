from django.apps import AppConfig


class DocumentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "documents"

    def ready(self) -> None:
        try:
            from documents.startup import ensure_default_schemas
            ensure_default_schemas()
        except Exception:
            # DB may not be ready yet (e.g. first run before migrations).
            # seed_data management command remains available as fallback.
            pass
