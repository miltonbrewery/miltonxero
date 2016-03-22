from django.db import models
from decimal import Decimal, ROUND_UP
from django.conf import settings

zero = Decimal("0.00")

def _round_up_to(amount, multiple):
    difference = amount % multiple
    if difference:
        amount = amount + multiple - difference
    return amount

def _vatinc_roundup_adjustment(item, current_price, multiple):
    vatinc_price = item.barrelsperitem * current_price * settings.VAT_MULTIPLIER
    desired_price = _round_up_to(vatinc_price, multiple)
    difference_inc_vat = desired_price - vatinc_price
    difference_ex_vat = difference_inc_vat / settings.VAT_MULTIPLIER
    difference_per_barrel = difference_ex_vat / item.barrelsperitem
    adjustment = difference_per_barrel.quantize(Decimal("0.01"))
    return adjustment

class PriceBand(models.Model):
    """A named group of pricing details."""
    name = models.CharField(max_length=40, unique=True)
    def __str__(self):
        return self.name
    @models.permalink
    def get_absolute_url(self):
        return ('invoicer.views.priceband',[self.pk])
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
            price = price + override.pricechange
            reasons.append(("Price adjustment", override.pricechange))
        except PriceOverride.DoesNotExist:
            pass
        # See if there is an extra charge for swaps
        if item.product.swap:
            try:
                config = ConfigOption.objects.get(
                    band=self, name="swap-premium")
                try:
                    adjustment = Decimal(config.value)
                except:
                    adjustment = zero
                price = price + adjustment
                reasons.append(("Swap premium", adjustment))
            except ConfigOption.DoesNotExist:
                pass
        # See if there is an adjustment for the unit size
        try:
            config = ConfigOption.objects.get(
                band=self, name=item.unitname + "-premium")
            try:
                adjustment = Decimal(config.value)
            except:
                adjustment = zero
            price = price + adjustment
            reasons.append((item.unitname.capitalize() + " premium", adjustment))
        except ConfigOption.DoesNotExist:
            pass
        # See if there's anything in the flags
        if "vat-roundup-pound" in item.flags:
            adjustment = _vatinc_roundup_adjustment(item, price, Decimal("1.00"))
            price = price + adjustment
            reasons.append(("Round up to whole pounds inc-VAT", adjustment))
        if "vat-roundup-50p" in item.flags:
            adjustment = _vatinc_roundup_adjustment(item, price, Decimal("0.50"))
            price = price + adjustment
            reasons.append(("Round up to £0.50 inc-VAT", adjustment))
            
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
    priceband = models.ForeignKey(PriceBand)
    account = models.CharField(max_length=10, blank=True) # xero account code
    name = models.CharField(max_length=500) # xero max is 500
    updated = models.DateTimeField()
    def __str__(self):
        return self.name
    @models.permalink
    def get_absolute_url(self):
        return ('invoicer.views.invoice',[self.xero_id])

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
        # This is used as the Xero item description
        return "{} ({}% ABV)".format(self.name,self.abv)
    @property
    def account(self):
        return settings.SWAP_ACCOUNT if self.swap else settings.DEFAULT_ACCOUNT
    class Meta:
        ordering = ['name']

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
    def __str__(self):
        return "{}/{}: {}: £{}".format(
            self.band.name, self.type.name, self.abv, self.price)

class PriceOverride(models.Model):
    """A price adjustment for a band/product combination"""
    band = models.ForeignKey(PriceBand)
    product = models.ForeignKey(Product)
    pricechange = models.DecimalField(max_digits=6, decimal_places=2)
    class Meta:
        unique_together = (
            ("band", "product"),
            )
    def __str__(self):
        return "{}: {}: adjust by £{}".format(
            self.band.name, self.product.name, self.pricechange)
