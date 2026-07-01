from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    zeebe_address: str = "localhost:26500"

    backend_core_url: str = "http://localhost:8000"
    backend_ocr_url: str = "http://localhost:8080"
    layout_service_url: str = "http://localhost:8090"
    langextract_service_url: str = "http://localhost:8091"

    docuparse_internal_service_token: str = ""

    # pyzeebe worker tuning
    worker_max_jobs: int = 5
    worker_poll_interval_ms: int = 100

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
