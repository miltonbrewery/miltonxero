from django.conf.urls import include, url
from . import views

urlpatterns = [
    url(r'^priceband/(?P<bandid>\d+)/$', views.priceband),
    url(r'^invoice/$', views.startinvoice),
    url(r'^invoice/(?P<contactid>[a-f0-9-]+)/$', views.invoice,
        name="invoice"),
    url(r'^bill/(?P<contactid>[a-f0-9-]+)/$', views.invoice, {'bill': True},
        name="bill"),
    url(r'^product/$', views.product),
    url(r'^product/(?P<productid>\d+)/$', views.product),
    url(r'^ajax/contact-completions.json$', views.contact_completions),
    url(r'^ajax/item-completions.json$', views.item_completions),
    url(r'^ajax/item-details.json$', views.item_details),
    url(r'^ajax/productcode-check.json$', views.productcode_check),
]
