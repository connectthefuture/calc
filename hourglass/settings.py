"""
Django settings for hourglass project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
import dj_database_url
import dj_email_url
from dotenv import load_dotenv
from typing import Tuple  # NOQA

from .settings_utils import (load_cups_from_vcap_services,
                             load_redis_url_from_vcap_services,
                             get_whitelisted_ips, is_running_tests)

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

DOTENV_PATH = os.path.join(BASE_DIR, '.env')

if os.path.exists(DOTENV_PATH):
    load_dotenv(DOTENV_PATH)

load_cups_from_vcap_services()
load_redis_url_from_vcap_services('calc-redis')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = 'DEBUG' in os.environ

HIDE_DEBUG_UI = 'HIDE_DEBUG_UI' in os.environ

if DEBUG:
    os.environ.setdefault(
        'SECRET_KEY',
        'I am an insecure secret key intended ONLY for dev/testing.'
    )
    os.environ.setdefault('EMAIL_URL', 'console:')
    if 'REDIS_URL' not in os.environ:
        # Only set a default REDIS_TEST_URL if REDIS_URL is not
        # explicitly defined either.
        os.environ.setdefault('REDIS_TEST_URL', 'redis://localhost:6379/1')
    os.environ.setdefault('REDIS_URL', 'redis://localhost:6379/0')
    os.environ.setdefault('DEFAULT_FROM_EMAIL', 'noreply@localhost')
    os.environ.setdefault('SERVER_EMAIL', 'system@localhost')

if 'EMAIL_URL' not in os.environ:
    raise Exception('Please define the EMAIL_URL environment variable!')

SEND_TRANSACTIONAL_EMAILS = os.environ['EMAIL_URL'] == 'dummy:'

email_config = dj_email_url.config()
# Sets a number of settings values, as described at
# https://github.com/migonzalvar/dj-email-url
vars().update(email_config)

DEFAULT_FROM_EMAIL = os.environ['DEFAULT_FROM_EMAIL']
SERVER_EMAIL = os.environ['SERVER_EMAIL']
HELP_EMAIL = os.environ.get('HELP_EMAIL', DEFAULT_FROM_EMAIL)

API_HOST = os.environ.get('API_HOST', '/api/')

GA_TRACKING_ID = os.environ.get('GA_TRACKING_ID', '')

ETHNIO_SCREENER_ID = os.environ.get('ETHNIO_SCREENER_ID')

NON_PROD_INSTANCE_NAME = os.environ.get('NON_PROD_INSTANCE_NAME')

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [
        os.path.join(BASE_DIR, 'hourglass/templates'),
    ],
    'APP_DIRS': True,
    'OPTIONS': {
        'context_processors': [
            'hourglass.context_processors.api_host',
            'hourglass.context_processors.show_debug_ui',
            'hourglass.context_processors.google_analytics_tracking_id',
            'hourglass.context_processors.ethnio_screener_id',
            'hourglass.context_processors.help_email',
            'hourglass.context_processors.non_prod_instance_name',
            'frontend.context_processors.is_safe_mode_enabled',
            "django.contrib.auth.context_processors.auth",
            "django.template.context_processors.debug",
            "django.template.context_processors.i18n",
            "django.template.context_processors.media",
            'django.template.context_processors.request',
            "django.template.context_processors.static",
            "django.template.context_processors.tz",
            "django.contrib.messages.context_processors.messages",
            "django.template.context_processors.request",
        ],
    },
}]

ALLOWED_HOSTS = ['*']


DATA_CAPTURE_APP_CONFIG = 'DefaultDataCaptureApp'

# When IS_RQ_SCHEDULER is in the env,
# instead use the special DataCaptureSchedulerApp since this process
# is being used as the scheduler instance.
if 'IS_RQ_SCHEDULER' in os.environ:
    DATA_CAPTURE_APP_CONFIG = 'DataCaptureSchedulerApp'


# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.humanize',
    'whitenoise.runserver_nostatic',
    'django.contrib.staticfiles',
    'debug_toolbar',
    'django_rq',

    'data_explorer',
    'contracts',
    'data_capture.apps.{}'.format(DATA_CAPTURE_APP_CONFIG),
    'api',
    'djorm_pgfulltext',
    'rest_framework',
    'corsheaders',
    'uaa_client',
    'user_account',
    'styleguide',
    'meta',
    'frontend',
)  # type: Tuple[str, ...]

if DEBUG:
    STATICFILES_STORAGE = 'frontend.crotchety.CrotchetyStaticFilesStorage'
    WHITENOISE_MIDDLEWARE = 'frontend.crotchety.CrotchetyWhiteNoiseMiddleware'
else:
    STATICFILES_STORAGE = ('whitenoise.storage.'
                           'CompressedManifestStaticFilesStorage')
    WHITENOISE_MIDDLEWARE = 'whitenoise.middleware.WhiteNoiseMiddleware'

MIDDLEWARE_CLASSES = (
    'django.middleware.cache.UpdateCacheMiddleware',
    'hourglass.middleware.ComplianceMiddleware',
    WHITENOISE_MIDDLEWARE,
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    # 'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # DjDT needs to be at the end of the middleware stack or else it can
    # cause issues with other middlewares' process_view methods
    # when the ProfilingPanel is enabled
    # http://django-debug-toolbar.readthedocs.io/en/stable/panels.html#profiling
    'hourglass.middleware.DebugOnlyDebugToolbarMiddleware',
    'django.middleware.cache.FetchFromCacheMiddleware',
)

AUTHENTICATION_BACKENDS = (
    'uaa_client.authentication.UaaBackend',
)

ROOT_URLCONF = 'hourglass.urls'

WSGI_APPLICATION = 'hourglass.wsgi.application'

# Internationalization
# https://docs.djangoproject.com/en/1.7/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# django cors headers
CORS_ORIGIN_ALLOW_ALL = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.7/howto/static-files/
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

STATICFILES_DIRS = (
    # os.path.join(BASE_DIR, 'static'),
)

RQ_QUEUES = {
    'default': {
        'URL': os.environ['REDIS_URL'],
    }
}

if is_running_tests():
    RQ_QUEUES['default']['URL'] = os.environ['REDIS_TEST_URL']

PAGINATION = 200

REST_FRAMEWORK = {
    'COERCE_DECIMAL_TO_STRING': False,
    'WHITELIST': get_whitelisted_ips(),
    'DEFAULT_PERMISSION_CLASSES': (
        'api.permissions.WhiteListPermission',
    ),
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] "
                      "%(message)s",
            'datefmt': "%d/%b/%Y %H:%M:%S"
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs/hourglass.log'),
            'formatter': 'verbose'
        },
        'contracts_file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs/load_data.log'),
            'formatter': 'verbose'
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'propagate': True,
            'level': 'INFO',
        },
        'contracts': {
            'handlers': ['console', 'contracts_file'],
            'propagate': True,
            'level': 'INFO',
        },
        'rq.worker': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'rq_scheduler': {
            'handlers': ['console'],
            'level': 'INFO',
        },
    },
}

DATABASES = {}
DATABASES['default'] = dj_database_url.config()

SECURE_SSL_REDIRECT = not DEBUG

if 'FORCE_DISABLE_SECURE_SSL_REDIRECT' in os.environ:
    SECURE_SSL_REDIRECT = False

SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = SECURE_SSL_REDIRECT

CSRF_COOKIE_HTTPONLY = True

# Amazon ELBs pass on X-Forwarded-Proto.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Amazon also sets X-Forwarded-Host.
USE_X_FORWARDED_HOST = True

SECRET_KEY = os.environ['SECRET_KEY']

ENABLE_SEO_INDEXING = 'ENABLE_SEO_INDEXING' in os.environ

SECURITY_HEADERS_ON_ERROR_ONLY = 'SECURITY_HEADERS_ON_ERROR_ONLY' in os.environ

DATA_CAPTURE_SCHEDULES = (
    'data_capture.schedules.s70.Schedule70PriceList',
)  # type: Tuple[str, ...]

if DEBUG and not HIDE_DEBUG_UI:
    DATA_CAPTURE_SCHEDULES += (
        'data_capture.schedules.fake_schedule.FakeSchedulePriceList',
    )

UAA_AUTH_URL = 'https://login.fr.cloud.gov/oauth/authorize'

UAA_TOKEN_URL = 'https://uaa.fr.cloud.gov/oauth/token'

UAA_CLIENT_ID = os.environ.get('UAA_CLIENT_ID', 'calc-dev')

UAA_CLIENT_SECRET = os.environ.get('UAA_CLIENT_SECRET')

LOGIN_URL = 'uaa_client:login'

LOGIN_REDIRECT_URL = '/'

# We *always* want to send a Cache-Control header downstream, especially
# in the event where we've got a reverse proxy with aggressive caching
# defaults like Amazon CloudFront in front of us.
#
# For now we're just going to tell any downstream caches to never cache
# any dynamic content we give them, to ensure that stale content never
# gets served to end-users.
CACHE_MIDDLEWARE_SECONDS = 0

if DEBUG:
    INSTALLED_APPS += ('fake_uaa_provider',)

if not UAA_CLIENT_SECRET:
    if DEBUG:
        # We'll be using the Fake UAA Provider.
        UAA_CLIENT_SECRET = 'fake-uaa-provider-client-secret'
        UAA_AUTH_URL = UAA_TOKEN_URL = 'fake:'
    else:
        raise Exception('UAA_CLIENT_SECRET must be defined in production.')

DEBUG_TOOLBAR_PATCH_SETTINGS = False

DEBUG_TOOLBAR_CONFIG = {
    'DISABLE_PANELS': set([
        'debug_toolbar.panels.redirects.RedirectsPanel',
        'debug_toolbar.panels.profiling.ProfilingPanel',
    ]),
    'SHOW_TOOLBAR_CALLBACK': 'hourglass.middleware.show_toolbar',
}

DEBUG_TOOLBAR_PANELS = [
    'data_capture.panels.DocsPanel',
    'debug_toolbar.panels.versions.VersionsPanel',
    'debug_toolbar.panels.profiling.ProfilingPanel',
    'debug_toolbar.panels.timer.TimerPanel',
    'debug_toolbar.panels.settings.SettingsPanel',
    'debug_toolbar.panels.headers.HeadersPanel',
    'debug_toolbar.panels.request.RequestPanel',
    'debug_toolbar.panels.sql.SQLPanel',
    'debug_toolbar.panels.staticfiles.StaticFilesPanel',
    'debug_toolbar.panels.templates.TemplatesPanel',
    'debug_toolbar.panels.cache.CachePanel',
    'debug_toolbar.panels.signals.SignalsPanel',
    'debug_toolbar.panels.logging.LoggingPanel',
    'debug_toolbar.panels.redirects.RedirectsPanel',
    'data_capture.panels.ScheduledJobsPanel',
]
