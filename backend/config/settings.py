"""
Django settings for home-camera-monitor project.
"""
import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv() -> None:
    """Load backend/.env for local dev; production uses systemd EnvironmentFile."""
    env_path = BASE_DIR / ".env"
    if not env_path.is_file():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv()

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-change-this-in-production-!@#$%^&*()",
)

DEBUG = os.environ.get("DJANGO_DEBUG", "True").lower() in ("true", "1", "yes")

AUTH_USER_MODEL = "accounts.User"

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
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "drf_yasg",
    # Local apps
    "apps.accounts",
    "apps.zones",
    "apps.alerts",
    "apps.events",
    "apps.detection",  # D-李东礼：危险区域与异常检测
    "apps.face",  # C-王梓铭：人脸识别与人数统计
    "apps.households",  # E-刘帅华：家庭管理
    "apps.video_stream",  # B-苏哲勋：MediaMTX + RTSP 视频预览
    "apps.reports",  # A：AI 监控日报
    "apps.notifications",  # 钉钉告警通知 + 逐级升级
]

# ── Detection config ─────────────────────────────────────────────────
# D-李东礼：检测参数可在 Django settings 中覆盖，未设置时使用 services.py 默认值

DETECTION_CONFIG = {
    # "FLOOD_AREA_THRESHOLD": 0.20,  # 示例：覆盖默认阈值
}

# 人脸特征 JSON 镜像；数据库中同时保存 FamilyMember.face_encoding。
FACE_REGISTRY_PATH = BASE_DIR / "registered_faces.json"
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.households.middleware.ActiveHouseholdMiddleware",
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
        "PASSWORD": os.environ.get("DB_PASSWORD", "Root@1234"),
        "HOST": os.environ.get("DB_HOST", "127.0.0.1"),
        "PORT": os.environ.get("DB_PORT", "3306"),
        "OPTIONS": {
            "charset": "utf8mb4",
        },
    }
}

# CI / 本地 pytest 使用 SQLite，无需 MySQL
if os.environ.get("CI"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "ci_test.sqlite3",
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
SNAPSHOT_ROOT = BASE_DIR / "snapshots"
CLIP_ROOT = BASE_DIR / "snapshots" / "clips"
EVENT_CLIP_ENABLED = os.getenv("EVENT_CLIP_ENABLED", "true").lower() in ("1", "true", "yes")
EVENT_CLIP_SECONDS = int(os.getenv("EVENT_CLIP_SECONDS", "10"))
FFMPEG_BIN = os.getenv("FFMPEG_BIN", "ffmpeg")
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LIVENESS_CONFIG = {
    "WINDOW_SIZE": int(os.getenv("LIVENESS_WINDOW_SIZE", "8")),
    "MIN_SAMPLES": int(os.getenv("LIVENESS_MIN_SAMPLES", "4")),
    "ALERT_COOLDOWN": int(os.getenv("LIVENESS_ALERT_COOLDOWN", "30")),
    "STATIC_MOTION_THRESHOLD": float(os.getenv("LIVENESS_STATIC_MOTION_THRESHOLD", "0.003")),
    "STATIC_BOX_THRESHOLD": float(os.getenv("LIVENESS_STATIC_BOX_THRESHOLD", "0.004")),
    "REPLAY_THRESHOLD": float(os.getenv("LIVENESS_REPLAY_THRESHOLD", "0.95")),
    "TEXTURE_THRESHOLD": float(os.getenv("LIVENESS_TEXTURE_THRESHOLD", "0.9")),
}

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
    # Swagger schema 由 drf-yasg 处理，不需要 DEFAULT_SCHEMA_CLASS
}

# ── SimpleJWT ────────────────────────────────────────────────────────

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=2),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "AUTH_HEADER_TYPES": ("Bearer",),
    # Token blacklist — 退出登录时将 refresh token 加入黑名单
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}

# ── DingTalk (钉钉) notification ─────────────────────────────────────

DINGTALK = {
    # 全局开关
    "ENABLED": os.environ.get("DINGTALK_ENABLED", "False").lower() in ("true", "1", "yes"),
    # 全局 fallback Webhook（如果家庭级别未配置则使用此地址）
    "WEBHOOK_URL": os.environ.get("DINGTALK_WEBHOOK_URL", ""),
    "SECRET": os.environ.get("DINGTALK_SECRET", ""),
    # 分级升级超时（秒），可被家庭级别的 DingTalkConfig 覆盖
    "ESCALATION_TIMEOUT_HIGH": int(os.environ.get("DINGTALK_ESCALATION_HIGH", "60")),
    "ESCALATION_TIMEOUT_MEDIUM": int(os.environ.get("DINGTALK_ESCALATION_MEDIUM", "300")),
    "ESCALATION_TIMEOUT_LOW": int(os.environ.get("DINGTALK_ESCALATION_LOW", "900")),
    # 最大升级层级（0=主R, 1=+1, 2=+2, 3=+3）
    "MAX_ESCALATION_LEVEL": int(os.environ.get("DINGTALK_MAX_ESCALATION", "3")),
    # 升级检查器轮询间隔（秒）
    "CHECKER_INTERVAL": int(os.environ.get("DINGTALK_CHECKER_INTERVAL", "30")),
    # 消息标题前缀
    "MESSAGE_TITLE_PREFIX": os.environ.get("DINGTALK_TITLE_PREFIX", "安防告警"),
}

# ── drf-yasg (Swagger) ───────────────────────────────────────────────

SWAGGER_SETTINGS = {
    "SECURITY_DEFINITIONS": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "JWT Token: Bearer <your_token>",
        }
    },
    "USE_SESSION_AUTH": False,
}

# ---------------------------------------------------------------------------
# 日志配置
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": "{levelname} {asctime} {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "loggers": {
        "apps.detection": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
