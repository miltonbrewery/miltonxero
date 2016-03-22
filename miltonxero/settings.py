"""
Django settings for miltonxero project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

def read(filename):
    with open(os.path.join(BASE_DIR, filename)) as f:
        return f.read().strip()

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = read('django-secret-key')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

ALLOWED_HOSTS = []

# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'invoicer',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'miltonxero.urls'

WSGI_APPLICATION = 'miltonxero.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.7/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'miltonxero',
    }
}

# Internationalization
# https://docs.djangoproject.com/en/1.7/topics/i18n/

LANGUAGE_CODE = 'en-gb'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.7/howto/static-files/

STATICFILES_DIRS = (
    os.path.join(BASE_DIR, "static"),
)

STATIC_URL = '/static/'

TEMPLATE_DIRS = (
    os.path.join(BASE_DIR, "templates"),
)

XERO_CONSUMER_KEY = read("consumer-key")

XERO_PRIVATE_KEY = read("private-key")

# List of (unit name, barrels, producttype, flags)
from decimal import Decimal
PRODUCT_UNITS = [
    ('pin', Decimal("0.125"), "Cask Ale", ["vat-roundup-50p"]),
    ('polypin', Decimal("0.125"), "Cask Ale", ["vat-roundup-pound"]),
    ('firkin', Decimal("0.25"), "Cask Ale", []),
    ('kil', Decimal("0.5"), "Cask Ale", []),
    ('barrel', Decimal("1.0"), "Cask Ale", []),
    ('30l keg', Decimal("0.1833"), "Craft Keg", []),
    ('50l keg', Decimal("0.3055"), "Craft Keg", []),
]

# Current VAT multiplier
VAT_MULTIPLIER = Decimal("1.20")

DEFAULT_ACCOUNT = "40000"
SWAP_ACCOUNT = "41000"
