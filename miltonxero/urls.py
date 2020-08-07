from django.urls import include, path
from django.contrib import admin

admin.autodiscover()

admin.site.site_header = 'Milton Invoice Tool'

import invoicer.urls

urlpatterns = [
    path('admin/', admin.site.urls),
] + invoicer.urls.urlpatterns
