import os
from pathlib import Path
import socket

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
SECRET_KEY = 'django-insecure-key-demo-cho-du-an-nay'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    # App chính của dự án
    'core',
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

ROOT_URLCONF = 'LogisticsProject.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'LogisticsProject.wsgi.application'

# ==============================================================================
# CẤU HÌNH DATABASE POSTGRESQL (DỰ PHÒNG SQLITE KHI THIẾU CỔNG 5432)
# ==============================================================================


def is_postgres_running(host='localhost', port=5432, timeout=0.6):
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


POSTGRES_DB_CONFIG = {
    'ENGINE': 'django.db.backends.postgresql',
    'NAME': os.environ.get('DB_NAME', 'logistics_db'),
    'USER': os.environ.get('DB_USER', 'postgres'),
    'PASSWORD': os.environ.get('DB_PASSWORD', '123'),
    'HOST': os.environ.get('DB_HOST', 'localhost'),
    'PORT': os.environ.get('DB_PORT', '5432'),
}

force_postgres = os.environ.get(
    'FORCE_POSTGRES', 'False'
).lower() in ('true', '1')

if force_postgres or is_postgres_running(
    POSTGRES_DB_CONFIG['HOST'], POSTGRES_DB_CONFIG['PORT']
):
    DATABASES = {'default': POSTGRES_DB_CONFIG}
    print(
        f"[DATABASE] Dang ket noi PostgreSQL: {POSTGRES_DB_CONFIG['NAME']} "
        f"tren {POSTGRES_DB_CONFIG['HOST']}:{POSTGRES_DB_CONFIG['PORT']}"
    )
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
    print(
        "[DATABASE] PostgreSQL chua ket noi tren port 5432, "
        "he thong dang khoi chay SQLite du phong de hoat dong on dinh!"
    )

# Password validation
AUTH_PWD_VALIDATOR_PATH = 'django.contrib.auth.password_validation.'
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': AUTH_PWD_VALIDATOR_PATH + 'UserAttributeSimilarityValidator',
    },
    {
        'NAME': AUTH_PWD_VALIDATOR_PATH + 'MinimumLengthValidator',
    },
    {
        'NAME': AUTH_PWD_VALIDATOR_PATH + 'CommonPasswordValidator',
    },
    {
        'NAME': AUTH_PWD_VALIDATOR_PATH + 'NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'vi'
TIME_ZONE = 'Asia/Ho_Chi_Minh'
USE_I18N = True
USE_TZ = True

# Static và Media files
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Cấu hình chuyển hướng Đăng nhập / Đăng xuất
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'
LOGIN_URL = 'core:login'

# CẤU HÌNH GỬI EMAIL BẰNG MAILTRAP (Mailbox hỗ trợ gửi thông báo)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'sandbox.smtp.mailtrap.io'
EMAIL_PORT = '2525'
EMAIL_HOST_USER = '5b6191184c3b45'
EMAIL_HOST_PASSWORD = 'fcc8d5b585aa1d'
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False
DEFAULT_FROM_EMAIL = 'FoodDelivery và Logistics <noreply@fooddelivery.com>'

REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    )
}
