from django.db import models
from django.db.models import Q
from decimal import Decimal, ROUND_UP
from django.conf import settings
from django.urls import reverse
import decimal

zero = Decimal("0.00")
penny = Decimal("0.01")
fifty_pence = Decimal("0.50")
pound = Decimal("1.00")


class CaseInsensitiveFieldMixin:
    """
    Field mixin that uses case-insensitive lookup alternatives if they exist.
    """
    LOOKUP_CONVERSIONS = {
        'exact': 'iexact',
        'contains': 'icontains',
        'startswith': 'istartswith',
        'endswith': 'iendswith',
        'regex': 'iregex',
    }
    def get_lookup(self, lookup_name):
        converted = self.LOOKUP_CONVERSIONS.get(lookup_name, lookup_name)
        return super().get_lookup(converted)


class CICharField(CaseInsensitiveFieldMixin, models.CharField):
    pass


class PriceBand(models.Model):
    """A named group of pricing details."""
    name = models.CharField(max_length=40, unique=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('priceband', args=[self.pk])

    def apply_rules_for(self, item):
        """Price per barrel, rules and account for an invoice item

        Work out the price per barrel; also record all the rules that were
        applied and the intermediate results.

        Return (price, account, list of rules)
        """
        rules = Price.objects.\
                filter(Q(band=self) | Q(band__isnull=True)).\
                filter(Q(type=item.product.type) | Q(type__isnull=True)).\
                filter(Q(abv=item.product.abv) | Q(abv__isnull=True)).\
                filter(Q(isSwap=item.product.swap) | Q(isSwap__isnull=True)).\
                filter(Q(isBill=item.isBill) | Q(isBill__isnull=True)).\
                filter(Q(product=item.product) | Q(product__isnull=True)).\
                filter(Q(unit=item.unit) | Q(unit__isnull=True)).\
                filter(Q(contact=item.contact) | Q(contact__isnull=True)).\
                order_by('priority').\
                all()
        price = zero
        account = "undefined"
        applied = []
        for r in rules:
            price, account = r.apply(item, price, account)
            applied.append((r, f"{price} / {account}"))
        return price, account, applied


class Contact(models.Model):
    """Extra details for Xero contacts.

    name is just a cache; it isn't used for auto-complete.  updated is
    the time the cache was last updated.  Additional cached fields:
    bill_{days,terms} and invoice_{days,terms}.
    """
    xero_id = models.CharField(max_length=36, unique=True) # uuid
    priceband = models.ForeignKey(PriceBand, on_delete=models.CASCADE)
    notes = models.CharField(max_length=500, blank=True, default='')
    name = models.CharField(max_length=500) # xero max is 500
    updated = models.DateTimeField()
    TERMS_CHOICES = (
        ("DAYSAFTERBILLDATE", "day(s) after bill date"),
        ("DAYSAFTERBILLMONTH", "day(s) after bill month"),
        ("OFCURRENTMONTH", "of the current month"),
        ("OFFOLLOWINGMONTH", "of the following month"),
    )
    bill_days = models.IntegerField(null=True, blank=True)
    bill_terms = models.CharField(max_length=20, choices=TERMS_CHOICES,
                                  blank=True)
    invoice_days = models.IntegerField(null=True, blank=True)
    invoice_terms = models.CharField(max_length=20, choices=TERMS_CHOICES,
                                     blank=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('invoice', args=[self.xero_id])


class ProductType(models.Model):
    """Type of product, eg. real ale or craft keg
    """
    name = models.CharField(max_length=80)

    def __str__(self):
        return self.name


class Unit(models.Model):
    """A unit in which products are sold"""
    name = models.CharField(max_length=10, help_text="Unit names with spaces "
                            "in may require code changes to work")
    size = models.DecimalField(max_digits=5, decimal_places=4,
                               help_text="Size in barrels")
    type = models.ForeignKey(ProductType, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class Product(models.Model):
    code = CICharField(max_length=30, unique=True) # xero max is 30
    name = models.CharField(max_length=80, unique=True) # XXX xero max is 50, and we're adding the ABV too
    abv = models.DecimalField(max_digits=3, decimal_places=1)
    type = models.ForeignKey(ProductType, on_delete=models.CASCADE)
    swap = models.BooleanField(default=True)
    sent = models.BooleanField(default=False, help_text="Has this product code "
                               "been sent to Xero yet?")

    def __str__(self):
        # This is used as the Xero item description
        return "{} ({}% ABV)".format(self.name,self.abv)

    class Meta:
        ordering = ['name']

    def get_absolute_url(self):
        return reverse('edit-product', args=[self.pk])


def _round_up_to(amount, multiple):
    difference = amount % multiple
    if difference:
        amount = amount + multiple - difference
    return amount

def _vatinc_roundup_adjustment(item, current_price, multiple):
    vatinc_price = item.unit.size * current_price * settings.VAT_MULTIPLIER
    desired_price = _round_up_to(vatinc_price, multiple)
    difference_inc_vat = desired_price - vatinc_price
    difference_ex_vat = difference_inc_vat / settings.VAT_MULTIPLIER
    difference_per_barrel = difference_ex_vat / item.unit.size
    adjustment = difference_per_barrel.quantize(penny)
    return adjustment

def _round_item_up_to(item, current_price, multiple):
    item_price = item.unit.size * current_price
    rounded_item_price = _round_up_to(item_price, multiple)
    rounded_barrel_price = rounded_item_price / item.unit.size
    return rounded_barrel_price


class ProgramRule(models.Model):
    """A pricing rule implemented in code"""
    name = models.CharField(max_length=80, unique=True)
    code = models.CharField(max_length=20)

    def __str__(self):
        return self.name

    def apply(self, item, price, account):
        if self.code == "vat-roundup-pound":
            price = price + _vatinc_roundup_adjustment(
                item, price, pound)
        elif self.code == "vat-roundup-50p":
            price = price + _vatinc_roundup_adjustment(
                item, price, fifty_pence)
        elif self.code == "barrel-roundup-pound":
            price = _round_up_to(price, pound)
        elif self.code == "item-roundup-pound":
            price = _round_item_up_to(item, price, pound)
        elif self.code == "item-roundup-50p":
            price = _round_item_up_to(item, price, fifty_pence)
        elif self.code == "multiply-by-abv":
            price = (price * item.product.abv).quantize(penny)
        elif self.code.startswith("multiply-by-"):
            try:
                price = (price * Decimal(self.code[12:])).quantize(penny)
            except decimal.InvalidOperation:
                pass

        return price, account


class Price(models.Model):
    """A rule applied to price calculations that match the criteria"""
    # Criteria:
    band = models.ForeignKey(PriceBand, blank=True, null=True,
                             on_delete=models.CASCADE)
    type = models.ForeignKey(ProductType, blank=True, null=True,
                             on_delete=models.CASCADE)
    abv = models.DecimalField(max_digits=3, decimal_places=1,
                              blank=True, null=True)
    isSwap = models.BooleanField(
        null=True,
        help_text="Match on whether the product has the 'swap' tickbox "
        "set; 'Unknown' matches either way")
    isBill = models.BooleanField(
        null=True,
        help_text="Match on whether we are preparing an invoice or a "
        "bill; 'Unknown' matches either way")
    product = models.ForeignKey(Product, blank=True, null=True,
                                on_delete=models.CASCADE)
    unit = models.ForeignKey(Unit, blank=True, null=True,
                             on_delete=models.CASCADE)
    contact = models.ForeignKey(Contact, blank=True, null=True,
                                on_delete=models.CASCADE)
    # Rules to apply:
    priority = models.IntegerField(
        default=100,
        help_text="Rules are applied in order of priority, with higher values "
        "being applied later")
    price = models.DecimalField(
        max_digits=6, decimal_places=2, blank=True, null=True,
        help_text="The amount to increase the price per barrel when this rule "
        "is applied")
    absolute_price = models.DecimalField(
        max_digits=6, decimal_places=2, blank=True, null=True,
        help_text="The new price per barrel when this rule is applied, ignoring "
        "prices set by any previous rules")
    rule = models.ForeignKey(
        ProgramRule, blank=True, null=True, on_delete=models.CASCADE,
        help_text="A programmed rule to alter the price and/or account")
    account = models.CharField(
        max_length=10, blank=True,
        help_text="The value to use for the Xero account when this rule is "
        "applied")
    # Just a comment, not used anywhere
    comment = models.CharField(
        max_length=80, blank=True)

    class Meta:
        ordering = ['priority']

    def __str__(self):
        things = []
        if self.band:
            things.append(self.band.name)
        if self.type:
            things.append(self.type.name)
        if self.abv:
            things.append(str(self.abv))
        if self.isSwap != None:
            things.append("swap" if self.isSwap else "not-swap")
        if self.isBill != None:
            things.append("bill" if self.isBill else "invoice")
        if self.product:
            things.append(str(self.product))
        if self.unit:
            things.append(self.unit.name)
        if self.contact:
            things.append(self.contact.name)
        criteria = " ".join(things) if things else "Always"
        things = []
        if self.price:
            things.append(f"add £{self.price}")
        if self.absolute_price != None:
            things.append(f"set £{self.absolute_price}")
        if self.rule:
            things.append(self.rule.name)
        if self.account:
            things.append("set account {}".format(self.account))
        actions = ", ".join(things) if things else "no effect"
        return f"{criteria}: {actions}"


    def apply(self, item, price, account):
        if self.price:
            price = price + self.price
        if self.absolute_price:
            price = self.absolute_price
        if self.rule:
            price, account = self.rule.apply(item, price, account)
        if self.account:
            account = self.account
        return price, account
