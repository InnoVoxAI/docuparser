from pathlib import Path
import os
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BASE_DIR.parent

for local_package_dir in (PROJECT_DIR / "contracts", PROJECT_DIR / "shared"):
    local_package_path = str(local_package_dir)
    if local_package_dir.exists() and local_package_path not in sys.path:
        sys.path.insert(0, local_package_path)

SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-test-key')

DEBUG = True

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'documents',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

if os.environ.get("POSTGRES_HOST"):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('POSTGRES_DB', 'docuparse'),
            'USER': os.environ.get('POSTGRES_USER', 'docuparse'),
            'PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'docuparse'),
            'HOST': os.environ.get('POSTGRES_HOST', 'postgres'),
            'PORT': os.environ.get('POSTGRES_PORT', '5432'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'

# Simple static API-only setup for this PoC workflow.
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
X_FRAME_OPTIONS = 'SAMEORIGIN'

BACKEND_OCR_URL = os.environ.get('BACKEND_OCR_URL', 'http://127.0.0.1:8080')
DOCUPARSE_LOCAL_EVENT_DIR = os.environ.get('DOCUPARSE_LOCAL_EVENT_DIR', str(BASE_DIR / '.docuparse-events'))
DOCUPARSE_LOCAL_STORAGE_DIR = os.environ.get('DOCUPARSE_LOCAL_STORAGE_DIR', str(PROJECT_DIR / '.docuparse-storage'))
DOCUPARSE_APPROVED_EXPORT_DIR = os.environ.get('DOCUPARSE_APPROVED_EXPORT_DIR', str(BASE_DIR / 'exports' / 'approved'))
DOCUPARSE_INTERNAL_SERVICE_TOKEN = os.environ.get('DOCUPARSE_INTERNAL_SERVICE_TOKEN', '').strip()
DOCUPARSE_AUTO_PROCESS_OCR = os.environ.get('DOCUPARSE_AUTO_PROCESS_OCR', 'true').strip().lower() not in {'0', 'false', 'no'}
