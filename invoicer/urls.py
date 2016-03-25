from django.conf.urls import patterns, include, url

urlpatterns = patterns(
    'invoicer.views',
    url(r'^priceband/(?P<bandid>\d+)/$', 'priceband'),
    url(r'^invoice/$', 'startinvoice'),
    url(r'^invoice/(?P<contactid>[a-f0-9-]+)/$', 'invoice'),
    url(r'^product/$', 'product'),
    url(r'^product/(?P<productid>\d+)/$', 'product'),
    url(r'^ajax/contact-completions.json$', 'contact_completions'),
    url(r'^ajax/item-completions.json$', 'item_completions'),
    url(r'^ajax/item-details.json$', 'item_details'),
    url(r'^ajax/productcode-check.json$', 'productcode_check'),
)
