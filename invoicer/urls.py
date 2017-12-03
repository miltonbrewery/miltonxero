from django.conf.urls import include, url
from . import views

urlpatterns = [
    url(r'^priceband/(?P<bandid>\d+)/$', views.priceband, name="priceband"),
    url(r'^invoice/$', views.startinvoice, name="new-invoice"),
    url(r'^invoice/(?P<contactid>[a-f0-9-]+)/$', views.invoice,
        name="invoice"),
    url(r'^bill/(?P<contactid>[a-f0-9-]+)/$', views.invoice, {'bill': True},
        name="bill"),
    url(r'^product/$', views.product, name="add-product"),
    url(r'^product/(?P<productid>\d+)/$', views.product, name="edit-product"),
    url(r'^ajax/contact-completions.json$', views.contact_completions,
        name="contact-completions"),
    url(r'^ajax/item-completions.json$', views.item_completions,
        name="item-completions"),
    url(r'^ajax/item-details.json$', views.item_details,
        name="item-details"),
    url(r'^ajax/productcode-check.json$', views.productcode_check),
]
