from miltonxero.settings import *

DEBUG = False

ALLOWED_HOSTS = ['milton-invoice.assorted.org.uk']

MEDIA_ROOT = os.path.join(os.path.dirname(BASE_DIR), "media")

MEDIA_URL = '/media/'

STATIC_ROOT = os.path.join(os.path.dirname(BASE_DIR), "static")

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': '/home/miltonxero/live/django.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'ERROR',
            'propagate': True,
        },
    },
}
