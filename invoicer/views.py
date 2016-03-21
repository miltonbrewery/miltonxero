from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect, Http404, JsonResponse
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.db import transaction
from django.utils import timezone
from django import forms
from django.conf import settings
from django.contrib import messages
from invoicer.models import *
from invoicer import xero
from decimal import Decimal, ROUND_HALF_UP
import datetime
import re
import codecs
import io
import csv

class UpdatePriceBandForm(forms.Form):
    table = forms.FileField(help_text="CSV file")
    clear_price_adjustments = forms.BooleanField(
        required=False, initial=False,
        help_text="Clear all product price adjustments for this price band.")

class _PricebandUpdateFailure(Exception):
    pass
@transaction.atomic
def _csv_to_priceband(band, cd):
    Price.objects.filter(band=band).delete()
    ConfigOption.objects.filter(band=band).delete()
    if cd['clear_price_adjustments']:
        PriceOverride.objects.filter(band=band).delete()

    c = csv.reader(io.StringIO(codecs.decode(cd['table'].read())))
    header = next(c)

    types = []
    
    for h in header[1:]:
        if not h:
            break
        try:
            ptype = ProductType.objects.get(name=h)
            types.append(ptype)
        except ProductType.DoesNotExist:
            raise _PricebandUpdateFailure("Product type '{}' does not exist"\
                                          .format(h))
    if not types:
        raise _PricebandUpdateFailure("No price band columns in file")

    for row in c:
        if not row[0]:
            continue
        abv = None
        try:
            abv = Decimal(row[0]).quantize(Decimal("0.1"))
        except:
            pass
        if abv:
            for ptype, price in zip(types, row[1:]):
                if price:
                    Price(band=band, type=ptype, abv=abv, price=price).save()
        else:
            ConfigOption(band=band, name=row[0], value=row[1]).save()

def priceband(request, bandid):
    """Information on a price band, and option to upload new data"""
    try:
        band = PriceBand.objects.get(pk=int(bandid))
    except PriceBand.DoesNotExist:
        raise Http404

    if request.method == 'POST':
        form = UpdatePriceBandForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                _csv_to_priceband(band, form.cleaned_data)
                messages.success(request, "Price band updated.")
                return HttpResponseRedirect("")
            except _PricebandUpdateFailure as e:
                messages.error(request, e.args[0])
    else:
        form = UpdatePriceBandForm()
    
    types = ProductType.objects.all()

    abvs = Price.objects.filter(band=band)\
                        .order_by('abv')\
                        .values('abv')\
                        .distinct()\
                        .all()
    abvs = [a['abv'] for a in abvs]

    prices = Price.objects.filter(band=band).all()
    pd = {(p.abv, p.type): p.price for p in prices}
    
    # Build list of (abv, price1, price2, ...) lists
    abvs = [[a] + [pd.get((a, t)) for t in types] for a in abvs]

    configs = ConfigOption.objects.filter(band=band).all()

    overrides = PriceOverride.objects.filter(band=band).all()
    
    return render(request, "invoicer/priceband.html",
                  {"band": band,
                   "types": types,
                   "abvs": abvs,
                   "configs": configs,
                   "overrides": overrides,
                   "form": form,
                   })

class ChooseContactForm(forms.Form):
    name = forms.CharField(label="Contact name", max_length=500)

def startinvoice(request):
    pricebands = PriceBand.objects.all()
    ptypes = ProductType.objects.all()
    if request.method == "POST":
        form = ChooseContactForm(request.POST)
        if form.is_valid():
            contacts = xero.get_contacts(form.cleaned_data['name'])
            if not contacts:
                form.add_error('name', "No contact exists with this name")
            elif len(contacts) == 1:
                return HttpResponseRedirect(
                    reverse(invoice, args=[contacts[0]["ContactID"]]))
            else:
                return render(request, 'invoicer/multicontact.html',
                              {"contacts": contacts})
    else:
        form = ChooseContactForm()

    return render(request, 'invoicer/startinvoice.html',
                  {"form": form,
                   "bands": pricebands,
                   "ptypes": ptypes})

class ContactOptionsForm(forms.Form):
    priceband = forms.ModelChoiceField(
        queryset=PriceBand.objects,
        label="Price band")
    account = forms.CharField(max_length=10, required=False,
                              help_text="Overrides accounts shown below")

class _XeroSendFailure(Exception):
    pass

def _send_to_xero(contactid, contact_extra, lines):
    # Interpret lines and build a set of products for this invoice
    products = set()
    invitems = []
    for l in lines:
        il = parse_item(l['item'], exactmatch=True)
        if len(il) != 1:
            raise _XeroSendFailure(
                "Ambiguous invoice item '{}'".format(l))
        item = il[0]
        products.add(item.product)
        invitems.append(item)

    # Send product details to Xero
    problem = xero.update_products(products)
    if problem:
        raise _XeroSendFailure("Received {} response when sending product "
                               "details to Xero".format(problem))

    try:
        invid = xero.send_invoice(
            contactid, contact_extra.default_priceband, invitems,
            override_account=contact_extra.account)
    except xero.Problem as e:
        raise _XeroSendFailure("Failed sending invoice to Xero: {}".format(e.args[0]))
    return invid

class InvoiceLineForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(InvoiceLineForm, self).__init__(*args, **kwargs)
        self.cp = None
        if "initial" in kwargs and "item" in kwargs['initial']:
            l = parse_item(kwargs['initial']['item'], exactmatch=True)
            if len(l) == 1:
                self.cp = l[0]
        # XXX wrong place to cache these - use InvoiceItem
        self.price = None
        self.reasons = None
    item = forms.CharField(max_length=500, required=True)
    def clean(self):
        cleaned_data = super(InvoiceLineForm, self).clean()
        if "item" not in cleaned_data:
            return
        l = parse_item(cleaned_data['item'], exactmatch=True)
        if not l:
            raise forms.ValidationError("Not a valid invoice line")
        if len(l) > 1:
            raise forms.ValidationError("Ambiguous invoice line")
        self.cp = l[0]
    def abv(self):
        return str(self.cp.product.abv)+"%" if self.cp else ""
    def barrels(self):
        return self.cp.barrels if self.cp else ""
    def get_price_and_reasons(self):
        # XXX this is the wrong place to cache these - use InvoiceItem
        if self.price:
            return
        if self.cp and self.priceband:
            self.price, self.reasons = self.priceband.price_for(self.cp)
    def barrelprice(self):
        if self.cp and self.priceband:
            self.get_price_and_reasons()
            return self.price
        return ""
    def barrelreasons(self):
        if self.cp and self.priceband:
            self.get_price_and_reasons()
            return self.reasons
        return []
    def totalprice(self):
        if self.cp and self.priceband:
            self.get_price_and_reasons()
            return (self.price * self.cp.barrels).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return ""
    def account(self):
        if self.cp:
            return self.cp.product.account
        return ""

class BaseInvoiceLineFormSet(forms.BaseFormSet):
    def __init__(self, priceband, *args, **kwargs):
        self.priceband = priceband
        super(BaseInvoiceLineFormSet, self).__init__(*args, **kwargs)
    def _construct_form(self, *args, **kwargs):
        # This is very much a hack, because we need to be compatible with
        # django-1.8; the option to pass kwargs to forms isn't introduced
        # until django-1.9.
        f = super(BaseInvoiceLineFormSet, self)._construct_form(*args, **kwargs)
        f.priceband = self.priceband
        return f

InvoiceLineFormSet = forms.formset_factory(
    InvoiceLineForm, formset=BaseInvoiceLineFormSet, extra=5, can_delete=True)

def invoice(request, contactid):
    try:
        contact_extra = Contact.objects.get(xero_id=contactid)
    except Contact.DoesNotExist:
        contact_extra = None
    # Look up the contact in xero if the cached info is out of date or absent
    if not contact_extra or \
       contact_extra.updated < (timezone.now() - datetime.timedelta(
           minutes=5)):
        contact = xero.get_contact(contactid)
        if not contact:
            raise Http404
        contactname = contact['Name']
    else:
        contactname = contact_extra.name
    if request.method == "POST":
        cform = ContactOptionsForm(request.POST)
        priceband = None
        if cform.is_valid():
            priceband = cform.cleaned_data['priceband']
        iform = InvoiceLineFormSet(priceband, request.POST,
                                   initial=request.session.get(contactid))
        if cform.is_valid() and iform.is_valid():
            if not contact_extra:
                contact_extra = Contact(xero_id=contactid)
            contact_extra.name = contactname
            contact_extra.updated = datetime.datetime.now()
            contact_extra.default_priceband = cform.cleaned_data['priceband']
            contact_extra.account = cform.cleaned_data['account']
            contact_extra.save()
            request.session[contactid] = [
                i for i in iform.cleaned_data if not i.get('DELETE',True)]
            if "send" in request.POST:
                try:
                    invid = _send_to_xero(contactid, contact_extra,
                                          request.session[contactid])
                    del request.session[contactid]
                    return HttpResponseRedirect(
                        "https://go.xero.com/AccountsReceivable/"
                        "Edit.aspx?InvoiceID=" + invid)
                except _XeroSendFailure as e:
                    messages.error(request, e.args[0])
            return HttpResponseRedirect("")
    else:
        initial = {}
        priceband = None
        if contact_extra:
            priceband = contact_extra.default_priceband
            initial['priceband'] = priceband
            initial['account'] = contact_extra.account
        cform = ContactOptionsForm(initial=initial)
        iform = InvoiceLineFormSet(
            priceband, initial=request.session.get(contactid))
    return render(request, 'invoicer/invoice.html',
                  {"contactname": contactname,
                   "cform": cform,
                   "iform": iform})

def contact_completions(request):
    q = request.GET['q']
    l = xero.get_contacts(q, use_contains=True)
    return JsonResponse([x["Name"] for x in l], safe=False)

itemre = re.compile(r'^(?P<qty>\d+)\s*(?P<unit>[\w]+?( keg)?)s?\s+(?P<product>[\w\s]+)$')

class InvoiceItem:
    def __init__(self, items, unitname, barrels, producttype, flags, product):
        self.items = items
        self.unitname = unitname
        self.barrelsperitem = barrels
        self.barrels = barrels * items
        self.producttype = producttype
        self.flags = flags
        self.product = product
        self._pricebands = {}
    def __str__(self):
        return "{} {}{} {}".format(
            self.items, self.unitname, "s" if self.items > 1 else "",
            self.product.name)
    def _fetch_price(self, priceband):
        if priceband not in self._pricebands:
            self._pricebands[priceband] = priceband.price_for(self)
    def priceperbarrel(self, priceband):
        self._fetch_price(priceband)
        return self._pricebands[priceband][0]
    def pricereasons(self, priceband):
        self._fetch_price(priceband)
        return self._pricebands[priceband][1]

def parse_item(description, exactmatch=False):
    """Convert an item description to a list of InvoiceItem objects
    """
    m = itemre.match(description)
    if not m:
        return []
    
    items = int(m.group('qty'))
    unitname = m.group('unit')
    product = m.group('product')
    if items < 1 or len(product) < 2:
        return []

    # Find all matching units
    mu = []
    for k in settings.PRODUCT_UNITS:
        if k[0].startswith(unitname):
            mu.append(k)

    # For each matching unit, search for matching products.  A product
    # matches either on the item code or product name if its type also
    # matches the unit.
    l = []
    if exactmatch:
        productfilter = Q(name=product)
    else:
        productfilter = Q(name__icontains=product) | Q(code__icontains=product)
    for name, barrels, producttype, flags in mu:
        products = Product.objects\
                          .filter(type__name=producttype)\
                          .filter(productfilter)\
                          .all()
        for p in products:
            l.append(InvoiceItem(items, name, barrels, producttype, flags, p))
    return l

def item_completions(request):
    q = request.GET['q']
    l = parse_item(q)
    return JsonResponse([str(i) for i in l], safe=False)

def item_details(request):
    q = request.GET['q']
    band = int(request.GET['band'])
    # band will be the pk - integer
    
    l = parse_item(q)
    if len(l) != 1:
        return JsonResponse({})
    i = l[0]
    d = {}
    #        price, reasons = 
    d = {
        'abv': i.abv,
        'barrels': i.barrels,
        'barrelprice': i.barrelprice,
        'total': 0.00,
    }
    return JsonResponse(d)
