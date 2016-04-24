# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

from decimal import Decimal

def set_priority_20(apps, schema_editor):
    Price = apps.get_model("invoicer", "Price")
    for p in Price.objects.all():
        p.priority = 20
        p.save()

def add_defaults(apps, schema_editor):
    PriceBand = apps.get_model("invoicer", "PriceBand")
    Price = apps.get_model("invoicer", "Price")
    ProgramRule = apps.get_model("invoicer", "ProgramRule")
    ProductType = apps.get_model("invoicer", "ProductType")
    ConfigOption = apps.get_model("invoicer", "ConfigOption")
    Product = apps.get_model("invoicer", "Product")
    Unit = apps.get_model("invoicer", "Unit")

    ProgramRule(name="Round up to £1 inc VAT", code="vat-roundup-pound").save()
    roundup = ProgramRule(name="Round up to 50p inc VAT", code="vat-roundup-50p")
    roundup.save()

    ipl = PriceBand.objects.get(name="Individual Pubs")
    trade = PriceBand.objects.get(name="Trade sales")
    private = PriceBand.objects.get(name="Private sales")

    trades = [ PriceBand.objects.get(name="Brewshed"),
               PriceBand.objects.get(name="Duty rate inter-brewery"),
               PriceBand.objects.get(name="Flat rate inter-brewery"),
    ]

    cask = ProductType.objects.get(name="Cask Ale")
    keg = ProductType.objects.get(name="Craft Keg")

    # Regular sales
    Price(type=cask, isSwap=False, isBill=False, account="40000", priority=10).save()
    Price(type=cask, isSwap=True, isBill=False, account="41000", priority=10).save()

    # Inter-brewery sales
    for t in trades:
        Price(type=cask, band=t, isBill=False, account="42000", priority=15).save()
    # All bills
    Price(isBill=True, account="50100", priority=15).save()

    # Swap premium
    Price(band=ipl, type=cask, isSwap=True, price=Decimal(10), priority=30).save()
    Price(band=trade, type=cask, isSwap=True, price=Decimal(10), priority=30).save()
    Price(band=private, type=cask, isSwap=True, price=Decimal(10), priority=30).save()

    # Private polypins - go through config options
    polypin = Unit.objects.get(name="polypin")
    for co in ConfigOption.objects.filter(band=private).all():
        if co.name.startswith("polypin-"):
            beername=co.name[8:]
            try:
                beer = Product.objects.get(name=beername)
                Price(band=private, product=beer, price=Decimal(co.value),
                      unit=polypin, priority=40).save()
            except Product.DoesNotExist:
                pass

    # Pins - round up to 50p inc VAT
    pin = Unit.objects.get(name="pin")
    Price(unit=pin, rule=roundup, priority=50).save()
    
    # Special case for Moravka
    moravka = Product.objects.get(code="Moravka")
    Price(product=moravka, price=Decimal(-74), account="44000", priority=50).save()

class Migration(migrations.Migration):

    dependencies = [
        ('invoicer', '0011_auto_20160424_1211'),
    ]

    operations = [
        migrations.RunPython(set_priority_20),
        migrations.RunPython(add_defaults),
    ]
