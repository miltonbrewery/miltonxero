from django.contrib import admin
from invoicer.models import *

class OverrideInline(admin.TabularInline):
    model = PriceOverride
    extra = 0
    can_delete = True

class ProductAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'abv', 'type', 'swap')
    list_filter = ('swap', 'sent')
    search_fields = ('code', 'name')
    ordering = ('name', )
    inlines = [OverrideInline]

class ConfigOptionAdmin(admin.ModelAdmin):
    list_display = ('band', 'name', 'value')
    list_filter = ('band', )

admin.site.register(PriceBand)
admin.site.register(ConfigOption, ConfigOptionAdmin)
admin.site.register(Contact)
admin.site.register(ProductType)
admin.site.register(Unit)
admin.site.register(Product, ProductAdmin)
admin.site.register(Price)
admin.site.register(PriceOverride)
