from django.conf.urls import patterns, include, url

urlpatterns = patterns(
    'invoicer.views',
    url(r'^priceband/(?P<bandname>\w+)/$', 'priceband'),
    url(r'^invoice/$', 'startinvoice'),
    url(r'^invoice/(?P<contactid>[a-f0-9-]+)/$', 'invoice'),
    url(r'^completions/contact.json$', 'contact_completions'),
    url(r'^completions/item.json$', 'item_completions'),
)
