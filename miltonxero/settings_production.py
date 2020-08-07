from miltonxero.settings import *

DEBUG = False

ALLOWED_HOSTS = ['milton-invoice.assorted.org.uk']

MEDIA_ROOT = os.path.join(os.path.dirname(BASE_DIR), "media")

MEDIA_URL = '/media/'

STATIC_ROOT = os.path.join(os.path.dirname(BASE_DIR), "static")
