from django.urls import path
from . import views

urlpatterns = [
    path('', views.startinvoice, name="new-invoice"),
    path('priceband/<int:bandid>/', views.priceband, name="priceband"),
    path('invoice/', views.startinvoice),
    path('invoice/<contactid>/', views.invoice, name="invoice"),
    path('bill/<contactid>/', views.invoice, {'bill': True},
         name="bill"),
    path('product/', views.product, name="add-product"),
    path('product/<int:productid>/', views.product, name="edit-product"),
    path('ajax/contact-completions.json', views.contact_completions,
         name="contact-completions"),
    path('ajax/item-completions.json', views.item_completions,
         name="item-completions"),
    path('ajax/item-details.json', views.item_details,
         name="item-details"),
    path('ajax/productcode-check.json', views.productcode_check),
    path('xero/callback/', views.xero_callback),
]
