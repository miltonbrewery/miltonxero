from django.db import models
from decimal import Decimal, ROUND_UP
from django.conf import settings

zero = Decimal("0.00")

class PriceBand(models.Model):
    """A named group of pricing details."""
    name = models.CharField(max_length=40)
    def __str__(self):
        return self.name
    def price_for(self, item):
        """Price per barrel for an invoice item

        Work out the price per barrel; also record how we did it.

        Return (price, list of (desc, amount))
        """
        reasons = []
        price = zero
        # Find the base price
        try:
            price = Price.objects.get(
                band=self, type=item.product.type,
                abv=item.product.abv)
            price = price.price
            reasons.append(("Base price", price))
        except Price.DoesNotExist:
            reasons.append(("No base price available", ""))
            return price, reasons
        # See if there is a price override and apply it if there is
        try:
            override = PriceOverride.objects.get(
                band=self, product=item.product)
            price = price + override
            reasons.append(("Price adjustment", override))
        except PriceOverride.DoesNotExist:
            pass
        # See if there is an extra charge for swaps
        if item.product.swap:
            try:
                config = ConfigOption.objects.get(
                    band=self, name="swap-premium")
                price = price + Decimal(config.value)
                reasons.append(("Swap premium", config.value))
            except ConfigOption.DoesNotExist:
                pass
        # See if there is an adjustment for the unit size
        try:
            config = ConfigOption.objects.get(
                band=self, name=item.unitname + "-premium")
            price = price + Decimal(config.value)
            reasons.append((item.unitname.capitalize() + " premium", config.value))
        except ConfigOption.DoesNotExist:
            pass
        # See if there's anything in the flags
        if "vat-roundup" in item.flags:
            vatinc_price = item.barrelsperitem * price * settings.VAT_MULTIPLIER
            desired_price = vatinc_price.quantize(
                Decimal("1."), rounding=ROUND_UP)
            difference_inc_vat = desired_price - vatinc_price
            difference_ex_vat = difference_inc_vat / settings.VAT_MULTIPLIER
            difference_per_barrel = difference_ex_vat / item.barrelsperitem
            adjustment = difference_per_barrel.quantize(Decimal("0.01"))
            price = price + adjustment
            reasons.append(("Round up to whole pounds inc-VAT", adjustment))
        return price, reasons

class ConfigOption(models.Model):
    """A value that can feed into pricing formulae"""
    band = models.ForeignKey(PriceBand)
    name = models.CharField(max_length=40)
    value = models.CharField(max_length=80)
    class Meta:
        unique_together = (
            ("band", "name"),
            )
    def __str__(self):
        return "{} {}: {}".format(self.band.name, self.name, self.value)

class Contact(models.Model):
    """Extra details for Xero contacts.

    name is just a cache; it isn't used for auto-complete.  updated is
    the time the cache was lated updated.
    """
    xero_id = models.CharField(max_length=36, unique=True) # uuid
    default_priceband = models.ForeignKey(PriceBand)
    account = models.CharField(max_length=10, blank=True) # xero account code
    name = models.CharField(max_length=500) # xero max is 500
    updated = models.DateTimeField()

class ProductType(models.Model):
    """Type of product, eg. real ale or craft keg
    """
    name = models.CharField(max_length=80)
    def price_for_abv(self, band, abv):
        try:
            price = Price.objects.get(band=band, type=self, abv=abv)
        except Price.DoesNotExist:
            return None
        return price.price
    def __str__(self):
        return self.name

class Product(models.Model):
    code = models.CharField(max_length=30, unique=True) # xero max is 30
    name = models.CharField(max_length=80, unique=True)
    abv = models.DecimalField(max_digits=3, decimal_places=1)
    type = models.ForeignKey(ProductType)
    swap = models.BooleanField(default=True)
    def __str__(self):
        return "{} ({}% ABV)".format(self.name,self.abv)
    def account(self):
        return settings.SWAP_ACCOUNT if self.swap else settings.DEFAULT_ACCOUNT

class Price(models.Model):
    """A regular price for a band/type/abv combination"""
    band = models.ForeignKey(PriceBand)
    type = models.ForeignKey(ProductType)
    abv = models.DecimalField(max_digits=3, decimal_places=1)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    class Meta:
        unique_together = (
            ("band", "type", "abv"),
        )

class PriceOverride(models.Model):
    """A price adjustment for a band/product combination"""
    band = models.ForeignKey(PriceBand)
    product = models.ForeignKey(Product)
    price = models.DecimalField(max_digits=6, decimal_places=2)
