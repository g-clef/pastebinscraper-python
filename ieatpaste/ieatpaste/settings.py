"""
Django settings for ieatpaste project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

from . import localsettings

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '$c8d(z7&0-%c%m2go08wt+j&5%4gj43=i!w9ln)!o2=_y%&g$='

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    'django.core.context_processors.request',
)

TEMPLATE_DIRS = (
    "/home/g-clef/ieatpaste/ieatpaste/templates",

)

AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend"

)

TEMPLATE_DEBUG = True

ALLOWED_HOSTS = ["ieatpaste.accessviolation.org",
                 "ieatpaste.g-clef.com",
                 "ieatpaste.g-clef.net",
                 "sparrow6.g-clef.net",
                 "192.168.1.206",
                 "71.178.167.65"]


# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    "paste",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "tastypie"
)

SITE_ID = 2

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'ieatpaste.urls'

WSGI_APPLICATION = 'ieatpaste.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

DATABASES = localsettings.DATABASES

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


ACCOUNT_USERNAME_REQUIRED = True
SOCIAL_ACCOUNT_QUERY_EMAIL = True
LOGIN_REDIRECT_URL = "/paste"
ACCOUNT_DEFAULT_HTTP_PROTOCOL = "https"
DEFAULT_FROM_EMAIL = "aaron@g-clef.net"

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/

STATIC_ROOT = "/home/g-clef/ieatpaste/ieatpaste/static"
STATIC_URL = '/static/'

ElasticsearchURL = localsettings.ElasticsearchURL
ElasticsearchIndex = localsettings.ElasticsearchIndex
ElasticsearchPercolateIndex = localsettings.ElasticsearchPercolateIndex