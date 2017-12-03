from django.conf.urls import include, url
from django.contrib import admin
admin.site.site_header = 'Milton Invoice Tool'
import invoicer.views, invoicer.urls

urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^$', invoicer.views.startinvoice),
    url(r'^', include(invoicer.urls.urlpatterns)),
]
