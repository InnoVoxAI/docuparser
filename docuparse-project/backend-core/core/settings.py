import os
import sys
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BASE_DIR.parent

for local_package_dir in (PROJECT_DIR / "contracts", PROJECT_DIR / "shared"):
    local_package_path = str(local_package_dir)
    if local_package_dir.exists() and local_package_path not in sys.path:
        sys.path.insert(0, local_package_path)

SECRET_KEY = os.environ.get("SECRET_KEY", "django-insecure-test-key")

DEBUG = True

ALLOWED_HOSTS = ["*"]

SHARED_APPS = [
    "django_tenants",
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.admin",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "tenants",
    "corsheaders",
    "users",
]

TENANT_APPS = [
    "documents",
]

INSTALLED_APPS = list(SHARED_APPS) + list(TENANT_APPS)

TENANT_MODEL = "tenants.Tenant"
TENANT_DOMAIN_MODEL = "tenants.Domain"

DATABASE_ROUTERS = ["django_tenants.routers.TenantSyncRouter"]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        # Resolve tanto o JWT do usuário quanto o token interno de serviço.
        # Sem isso, chamadas com o token interno (Bearer <token>) seriam
        # rejeitadas pela JWTAuthentication antes de qualquer verificação.
        "users.authentication.DocuparseAuthentication",
    ],
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=12),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

CORS_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "CORS_ALLOWED_ORIGINS", "https://docuparser.innovox.ai"
    ).split(",")
    if o.strip()
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "tenants.middleware.JWTTenantMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"

# Database selection, in priority order: DATABASE_URL → POSTGRES_HOST → SQLite.
#
# The SQLite fallback writes to a file *inside the container* (BASE_DIR/db.sqlite3), which
# is ephemeral: it is wiped on every deploy/restart, silently destroying all data. To stop
# production from ever booting on it, set DOCUPARSE_REQUIRE_POSTGRES=true — the app will then
# refuse to start unless a real PostgreSQL connection is configured. Defaults to off so local
# and dev (SQLite) keep working unchanged.
_database_url = os.environ.get("DATABASE_URL", "").strip()
_require_postgres = os.environ.get(
    "DOCUPARSE_REQUIRE_POSTGRES", "false"
).strip().lower() in {"1", "true", "yes"}

if _database_url:
    from urllib.parse import unquote, urlparse

    _parsed = urlparse(_database_url)
    if _parsed.scheme not in ("postgres", "postgresql"):
        from django.core.exceptions import ImproperlyConfigured

        raise ImproperlyConfigured(
            f"Unsupported DATABASE_URL scheme: {_parsed.scheme!r} (expected postgres://)"
        )
    DATABASES = {
        "default": {
            "ENGINE": "django_tenants.postgresql_backend",
            "NAME": (_parsed.path or "/docuparse").lstrip("/") or "docuparse",
            "USER": unquote(_parsed.username or ""),
            "PASSWORD": unquote(_parsed.password or ""),
            "HOST": _parsed.hostname or "",
            "PORT": str(_parsed.port or "5432"),
        }
    }
elif os.environ.get("POSTGRES_HOST"):
    DATABASES = {
        "default": {
            "ENGINE": "django_tenants.postgresql_backend",
            "NAME": os.environ.get("POSTGRES_DB", "docuparse"),
            "USER": os.environ.get("POSTGRES_USER", "docuparse"),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "docuparse"),
            "HOST": os.environ.get("POSTGRES_HOST", "postgres"),
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        }
    }
elif _require_postgres:
    from django.core.exceptions import ImproperlyConfigured

    raise ImproperlyConfigured(
        "DOCUPARSE_REQUIRE_POSTGRES is set but no DATABASE_URL/POSTGRES_HOST was provided. "
        "Refusing to start on the ephemeral in-container SQLite database to avoid data loss. "
        "Configure a persistent PostgreSQL database for production."
    )
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

# Simple static API-only setup for this PoC workflow.
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
X_FRAME_OPTIONS = "SAMEORIGIN"

BACKEND_OCR_URL = os.environ.get("BACKEND_OCR_URL", "http://127.0.0.1:8080")
LANGEXTRACT_SERVICE_URL = os.environ.get(
    "LANGEXTRACT_SERVICE_URL", "http://127.0.0.1:8091"
)
DOCUPARSE_LOCAL_EVENT_DIR = os.environ.get(
    "DOCUPARSE_LOCAL_EVENT_DIR", str(BASE_DIR / ".docuparse-events")
)
# Exporta o default local do serviço para o ambiente, de modo que
# docuparse_storage.get_storage() (que lê a config exclusivamente de
# DOCUPARSE_LOCAL_STORAGE_DIR no ambiente) preserve o caminho histórico deste
# serviço sem precisar receber o diretório por argumento.
os.environ.setdefault(
    "DOCUPARSE_LOCAL_STORAGE_DIR", str(PROJECT_DIR / ".docuparse-storage")
)
DOCUPARSE_LOCAL_STORAGE_DIR = os.environ["DOCUPARSE_LOCAL_STORAGE_DIR"]
# Storage compartilhado de objetos (feature 011). O backend é selecionado por
# DOCUPARSE_STORAGE_BACKEND (default 'local' preserva o comportamento atual) e
# consumido por docuparse_storage.get_storage(). Endpoint/bucket/credenciais vêm
# sempre do ambiente/secret. Ver docs/specs/011-shared-object-storage.
DOCUPARSE_STORAGE_BACKEND = (
    os.environ.get("DOCUPARSE_STORAGE_BACKEND", "local").strip().lower()
)
S3_ENDPOINT_URL = os.environ.get("S3_ENDPOINT_URL", "").strip()
S3_BUCKET = os.environ.get("S3_BUCKET", "").strip()
S3_REGION = os.environ.get("S3_REGION", "").strip()
DOCUPARSE_APPROVED_EXPORT_DIR = os.environ.get(
    "DOCUPARSE_APPROVED_EXPORT_DIR", str(BASE_DIR / "exports" / "approved")
)
DOCUPARSE_INTERNAL_SERVICE_TOKEN = os.environ.get(
    "DOCUPARSE_INTERNAL_SERVICE_TOKEN", ""
).strip()
DOCUPARSE_AUTO_PROCESS_OCR = os.environ.get(
    "DOCUPARSE_AUTO_PROCESS_OCR", "true"
).strip().lower() not in {"0", "false", "no"}
DOCUPARSE_AUTO_PROCESS_EXTRACTION = os.environ.get(
    "DOCUPARSE_AUTO_PROCESS_EXTRACTION", "true"
).strip().lower() not in {"0", "false", "no"}

# Sem uma config explícita, loggers fora da árvore 'django' (documents.*) não têm
# handler e caem no lastResort do Python, que descarta INFO e emite só WARNING+.
# Era por isso que uma falha de pipeline aparecia como uma única linha sem causa.
DOCUPARSE_LOG_LEVEL = os.environ.get("DOCUPARSE_LOG_LEVEL", "INFO").strip().upper()
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {"format": "%(levelname)s %(asctime)s %(name)s: %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "standard"},
    },
    "root": {"handlers": ["console"], "level": DOCUPARSE_LOG_LEVEL},
    # propagate=False: senão as mensagens do Django sairiam duplicadas (handler
    # próprio do DEFAULT_LOGGING + o handler do root definido acima).
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False}
    },
}

# Defaults for the per-tenant OCRSettings/EmailSettings singletons (documents/models.py).
# Configurable via env so a fallback model/URL isn't baked into the model definition itself.
OPENROUTER_FALLBACK_MODEL = os.environ.get(
    "OPENROUTER_FALLBACK_MODEL", "qwen/qwen2.5-vl-72b-instruct"
)
EMAIL_WEBHOOK_URL = os.environ.get(
    "EMAIL_WEBHOOK_URL", "http://127.0.0.1:8070/api/v1/email/messages"
)
