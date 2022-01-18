from django.contrib import admin
from invoicer.models import *

class ProductAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'abv', 'type', 'swap')
    list_filter = ('swap', 'sent')
    search_fields = ('code', 'name')
    ordering = ('name', )

class PriceAdmin(admin.ModelAdmin):
    list_filter = ('band', 'type', 'unit', 'priority')
    ordering = ('priority',)
    list_display = ('__str__', 'priority', 'comment')
    fieldsets = (
        ("Criteria", {
            'description': "This price rule will apply when all the following "
            "criteria match.  Criteria that are blank or \"unknown\" will match "
            "anything.  It's possible to create rules that will never match, "
            "for example a 5.5% Sparta or Cask Ale sold in 30l kegs; doing so "
            "is pointless but harmless.",
            'fields': ('band', 'type', 'abv', 'isSwap', 'isBill',
                       'product', 'unit', 'contact'),
        }),
        ("Actions", {
            'description': "Actions to apply when the criteria match.  If "
            "multiple actions are specified, they are applied in the order "
            "shown below, i.e. price change applies before rule.",
            'fields': ('priority', 'price', 'absolute_price', 'rule', 'account'),
        }),
        ("Comment", {
            'fields': ('comment', ),
        }),
    )

class ContactAdmin(admin.ModelAdmin):
    list_display = ('name', 'priceband', 'notes')
    list_filter = ('priceband', )
    search_fields = ('name', 'notes')

admin.site.register(PriceBand)
admin.site.register(Contact, ContactAdmin)
admin.site.register(ProductType)
admin.site.register(Unit)
admin.site.register(Product, ProductAdmin)
admin.site.register(Price, PriceAdmin)
admin.site.register(ProgramRule)
