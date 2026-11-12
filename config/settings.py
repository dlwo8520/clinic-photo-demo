import os
import hashlib
import secrets
import ipaddress
from pathlib import Path
from urllib.parse import urlsplit
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
ON_RENDER = os.environ.get("RENDER", "").lower() == "true"
DEBUG = os.environ.get("DJANGO_DEBUG", "0" if ON_RENDER else "1").lower() in {"1", "true", "yes"}
if ON_RENDER and DEBUG:
    raise ImproperlyConfigured("Render requires DJANGO_DEBUG=0")
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured("DJANGO_DEBUG=0 requires DJANGO_SECRET_KEY")
    secret_path = BASE_DIR / ".local_secret_key"
    try:
        with secret_path.open("x", encoding="utf-8") as secret_file:
            secret_file.write(secrets.token_urlsafe(64))
    except FileExistsError:
        pass
    SECRET_KEY = secret_path.read_text(encoding="utf-8")
if not DEBUG:
    if len(SECRET_KEY) < 32 or len(set(SECRET_KEY)) < 5 or SECRET_KEY.startswith("django-insecure-"):
        raise ImproperlyConfigured("Production DJANGO_SECRET_KEY must be a random secret of at least 32 characters")
    if len(SECRET_KEY) < 50:
        SECRET_KEY = hashlib.sha512(SECRET_KEY.encode()).hexdigest()
default_hosts = "localhost,127.0.0.1,[::1]" if DEBUG else os.environ.get("RENDER_EXTERNAL_HOSTNAME", "")
ALLOWED_HOSTS = [h.strip().lower() for h in os.environ.get("DJANGO_ALLOWED_HOSTS", default_hosts).split(",") if h.strip()]
QR_BASE_URL = os.environ.get("QR_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
qr_parts = urlsplit(QR_BASE_URL)
if qr_parts.scheme not in {"http", "https"} or not qr_parts.netloc or qr_parts.path or qr_parts.query or qr_parts.fragment or qr_parts.username:
    raise ImproperlyConfigured("QR_BASE_URL must be an http(s) origin, e.g. http://192.168.0.10:8000")
if not DEBUG:
    if not ALLOWED_HOSTS or any(h.startswith(".") or "*" in h or "/" in h or ":" in h for h in ALLOWED_HOSTS):
        raise ImproperlyConfigured("Production DJANGO_ALLOWED_HOSTS requires explicit domain names without wildcards or ports")
    host = (qr_parts.hostname or "").lower().rstrip(".")
    local_host = host == "localhost" or host.endswith((".localhost", ".local", ".internal", ".test")) or "." not in host
    try:
        local_host = local_host or not ipaddress.ip_address(host).is_global
    except ValueError:
        pass
    if "QR_BASE_URL" not in os.environ or qr_parts.scheme != "https" or local_host:
        raise ImproperlyConfigured("Production QR_BASE_URL must explicitly specify the public HTTPS origin, never localhost or a private IP")
    if host not in ALLOWED_HOSTS:
        raise ImproperlyConfigured("QR_BASE_URL hostname must be in DJANGO_ALLOWED_HOSTS")
data_value = os.environ.get("CLINIC_DATA_DIR", "")
STORAGE_MODE = os.environ.get("CLINIC_STORAGE_MODE", "persistent" if ON_RENDER else "local")
if STORAGE_MODE not in {"local", "ephemeral", "persistent"}:
    raise ImproperlyConfigured("CLINIC_STORAGE_MODE must be local, ephemeral or persistent")
DEMO_LOGIN_ENABLED = os.environ.get("CLINIC_DEMO_LOGIN", "0").lower() in {"1", "true", "yes"}
if not DEBUG and (not data_value or not Path(data_value).is_absolute()):
    raise ImproperlyConfigured("Production CLINIC_DATA_DIR must be an absolute directory")
DATA_DIR = Path(data_value).resolve() if data_value else BASE_DIR
UPLOAD_SESSION_MINUTES = 10
INSTALLED_APPS = [
    "django.contrib.auth", "django.contrib.contenttypes", "django.contrib.sessions",
    "django.contrib.messages", "django.contrib.staticfiles", "clinic",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "clinic.middleware.PrivateResponseMiddleware",
    "clinic.middleware.UploadSizeMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates", "DIRS": [], "APP_DIRS": True,
              "OPTIONS": {"context_processors": ["django.template.context_processors.request", "django.contrib.auth.context_processors.auth", "django.contrib.messages.context_processors.messages"]}}]
WSGI_APPLICATION = "config.wsgi.application"
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": DATA_DIR / "db.sqlite3", "OPTIONS": {"timeout": 20}}}
AUTH_PASSWORD_VALIDATORS = [{"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"}, {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"}]
LANGUAGE_CODE = "ko-kr"
TIME_ZONE = "Asia/Seoul"
USE_I18N = True
USE_TZ = True
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {"default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
            "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage" if DEBUG else "whitenoise.storage.CompressedManifestStaticFilesStorage"}}
# No MEDIA_URL or public media serving route. All photos pass the staff gate.
PRIVATE_MEDIA_ROOT = DATA_DIR / "private_media"
# Multipart request scratch files use the OS private temp directory and Django
# removes them when the request closes. Accepted originals/display/thumbs all
# live under PRIVATE_MEDIA_ROOT. Free demo storage is ephemeral. No import-time writes.
FILE_UPLOAD_TEMP_DIR = None
FILE_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024
DATA_UPLOAD_MAX_NUMBER_FILES = 20
DATA_UPLOAD_MAX_NUMBER_FIELDS = 100
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_BATCH_BYTES = 100 * 1024 * 1024
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/patients/"
LOGOUT_REDIRECT_URL = "/login/"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 8 * 60 * 60
SECURE_CONTENT_TYPE_NOSNIFF = True
# Native form POSTs can send Origin:null with no-referrer. Preserve same-origin
# form origins/referers while withholding private upload URLs from other sites.
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    SECURE_REDIRECT_EXEMPT = [r"^healthz/$"]
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    CSRF_TRUSTED_ORIGINS = [v.strip() for v in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", QR_BASE_URL).split(",") if v.strip()]
