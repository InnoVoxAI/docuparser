import logging
from pathlib import Path

import toml
from atoms.config import settings
from atoms.email_reader import email_reader_router
from atoms.fastapi_decorator import create_lifespan_with_daemons
from atoms.logging import configure_logging
from atoms.whatsapp import twilio_router
from atoms.whatsapp import twilio_webhook_router
from fastapi import APIRouter
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

configure_logging(
    level="DEBUG",
    json_logs=False,
)

router = APIRouter()
router.include_router(email_reader_router)
router.include_router(twilio_router)
router.include_router(twilio_webhook_router)


@router.post("/echo_data")
async def echo_data(data: dict):
    return {"message": "Data received", "data": data}


def setup_logging():
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger(__name__)
    return logger


def get_project_version():
    version = "unknown"
    # adopt path to your pyproject.toml
    pyproject_toml_file = Path(__file__).parent / "../pyproject.toml"
    if pyproject_toml_file.exists() and pyproject_toml_file.is_file():
        data = toml.load(pyproject_toml_file)
        # check project.version
        if "project" in data and "version" in data["project"]:
            version = data["project"]["version"]
        # check tool.poetry.version
        elif (
            "tool" in data
            and "poetry" in data["tool"]
            and "version" in data["tool"]["poetry"]
        ):
            version = data["tool"]["poetry"]["version"]
    return version


version = get_project_version()

app = FastAPI(
    title=settings.title,
    description=settings.description,
    version=version,
    openapi_url=f"{settings.openapi_url}",
    root_path=settings.root_path,
    lifespan=create_lifespan_with_daemons(),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
)


app.include_router(router)
