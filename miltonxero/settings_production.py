from miltonxero.settings import *

DEBUG = False
TEMPLATE_DEBUG = DEBUG

ALLOWED_HOSTS = ['*']

MEDIA_ROOT = os.path.join(os.path.dirname(BASE_DIR), "media")

MEDIA_URL = '/media/'

STATIC_ROOT = os.path.join(os.path.dirname(BASE_DIR), "static")
