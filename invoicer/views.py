from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect, Http404, JsonResponse
from django.db.models import Q
from django import forms
from django.conf import settings
from invoicer.models import *
from invoicer import xero
from decimal import Decimal, ROUND_HALF_UP
import datetime
import re

def _load_prices(band):
    prices = Price.objects.filter(band=band).all()
    pd = {(p.abv, p.type): p.price for p in prices}
    return pd

def priceband(request, bandname):
    """Information on a price band, and option to upload new data"""
    try:
        band = PriceBand.objects.get(name=bandname)
    except PriceBand.DoesNotExist:
        raise Http404

    types = ProductType.objects.all()

    abvs = Price.objects.filter(band=band)\
                        .order_by('abv')\
                        .values('abv')\
                        .distinct()\
                        .all()
    abvs = [a['abv'] for a in abvs]

    pd = _load_prices(band)
    
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
                   })

class ChooseContactForm(forms.Form):
    name = forms.CharField(label="Contact name", max_length=500)

def startinvoice(request):
    if request.method == "POST":
        form = ChooseContactForm(request.POST)
        if form.is_valid():
            contacts = xero.get_contacts(form.cleaned_data['name'])
            if not contacts:
                form.add_error('name', "No contact exists with this name")
            elif len(contacts) == 1:
                return HttpResponseRedirect(contacts[0]["ContactID"] + "/")
            else:
                return render(request, 'invoicer/multicontact.html',
                              {"contacts": contacts})
    else:
        form = ChooseContactForm()

    return render(request, 'invoicer/startinvoice.html',
                  {"form": form})

class ContactOptionsForm(forms.Form):
    priceband = forms.ModelChoiceField(
        queryset=PriceBand.objects,
        label="Price band")
    account = forms.CharField(max_length=10, required=False,
                              help_text="Overrides accounts shown below")

class InvoiceLineForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(InvoiceLineForm, self).__init__(*args, **kwargs)
        self.cp = None
        if "initial" in kwargs and "item" in kwargs['initial']:
            l = parse_item(kwargs['initial']['item'], exactmatch=True)
            if len(l) == 1:
                self.cp = l[0]
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
        if self.price:
            return
        if self.cp:
            self.price, self.reasons = self.priceband.price_for(self.cp)
    def barrelprice(self):
        if self.cp:
            self.get_price_and_reasons()
            return self.price
        return ""
    def barrelreasons(self):
        if self.cp:
            self.get_price_and_reasons()
            return self.reasons
        return []
    def totalprice(self):
        if self.cp:
            self.get_price_and_reasons()
            return (self.price * self.cp.barrels).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return ""
    def account(self):
        if self.cp:
            return self.cp.product.account()
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
       contact_extra.updated < (datetime.datetime.now() - datetime.timedelta(
           minutes=5)):
        contact = xero.get_contact(contactid)
        if not contact:
            raise Http404
        contactname = contact['Name']
    else:
        contactname = contact_extra.name
    if request.method == "POST":
        cform = ContactOptionsForm(request.POST)
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

    def __str__(self):
        return "{} {}{} {}".format(
            self.items, self.unitname, "s" if self.items > 1 else "",
            self.product.name)

def parse_item(description, exactmatch=False):
    """Convert an item description to a list of (quantity, unit, product)
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
