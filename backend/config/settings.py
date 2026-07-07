"""
Django settings for home-camera-monitor project.
"""
import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-change-this-in-production-!@#$%^&*()",
)

DEBUG = os.environ.get("DJANGO_DEBUG", "True").lower() in ("true", "1", "yes")

ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",")

# ── Application definition ──────────────────────────────────────────

INSTALLED_APPS = [
    # Django built-in
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "drf_spectacular",
    # Local apps
    "apps.accounts",
    "apps.zones",
    "apps.alerts",
    "apps.events",
    "apps.detection",  # D-李东礼：危险区域与异常检测
]

# ── Detection config ─────────────────────────────────────────────────
# D-李东礼：检测参数可在 Django settings 中覆盖，未设置时使用 services.py 默认值

DETECTION_CONFIG = {
    # "FLOOD_AREA_THRESHOLD": 0.20,  # 示例：覆盖默认阈值
}

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

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

WSGI_APPLICATION = "config.wsgi.application"

# ── Database ─────────────────────────────────────────────────────────

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.environ.get("DB_NAME", "home_camera_monitor"),
        "USER": os.environ.get("DB_USER", "root"),
        "PASSWORD": os.environ.get("DB_PASSWORD", ""),
        "HOST": os.environ.get("DB_HOST", "127.0.0.1"),
        "PORT": os.environ.get("DB_PORT", "3306"),
        "OPTIONS": {
            "charset": "utf8mb4",
        },
    }
}

# ── Password validation ──────────────────────────────────────────────

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ── Internationalization ─────────────────────────────────────────────

LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_TZ = True

# ── Static files ────────────────────────────────────────────────────

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── CORS ─────────────────────────────────────────────────────────────

CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",  # Vite dev server
    "http://127.0.0.1:5173",
]

# ── DRF ─────────────────────────────────────────────────────────────

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

# ── SimpleJWT ────────────────────────────────────────────────────────

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=2),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# ── drf-spectacular (Swagger) ────────────────────────────────────────

SPECTACULAR_SETTINGS = {
    "TITLE": "Home Camera Monitor API",
    "DESCRIPTION": "居家智能摄像头监控系统 — 业务 API 文档",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}
