from django.conf.urls import patterns, include, url
from django.contrib import admin
admin.site.site_header = 'Milton Invoice Tool'

urlpatterns = patterns(
    '',
    # Examples:
    # url(r'^$', 'miltonxero.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^$', 'invoicer.views.startinvoice'),
    url(r'^', include('invoicer.urls')),
)
