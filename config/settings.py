"""
Django settings for dkcloud project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# Secrets file
from . import secrets

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
#SECRET_KEY = '2w7wu517#^8^1o!^2-dqyv^itig&@^o+!=jjvnuwop#m#&izs$'
SECRET_KEY = secrets.SECRET_KEY

# SECURITY WARNING: don't run with debug turned on in production!
#DEBUG = True
DEBUG = secrets.DEBUG

#TEMPLATE_DEBUG = True
TEMPLATE_DEBUG = secrets.TEMPLATE_DEBUG

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'south',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'dkcloud.urls'

WSGI_APPLICATION = 'dkcloud.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': secrets.DATABASE_NAME,
        'USER': secrets.DATABASE_USER,
        'PASSWORD': secrets.DATABASE_PASSWORD,
        #'HOST': secrets.DATABASE_HOST,
        #'PORT': secrets.DATABASE_PORT,
    }
}

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = '/var/www/{{domain}}/{{app_name}}/static/'

# Email Settings
EMAIL_HOST_USER = secrets.MAIL_USER
EMAIL_HOST_PASSWORD = secrets.MAIL_PASSWORD

# Allowed Hosts
ALLOWED_HOSTS = ['.{{domain}}',
                 '.{{domain}}.',]