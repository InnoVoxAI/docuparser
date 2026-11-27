from django.apps import AppConfig


class JobqueueConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "jobqueue"
    verbose_name = "Fila de processamento"
