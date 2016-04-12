from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect, Http404, JsonResponse
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.db import transaction
from django.utils import timezone
from django import forms
from django.conf import settings
from django.contrib import messages
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
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
    def __init__(self, message):
        self.message = message

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

@login_required
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
                messages.error(request, e.message)
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

@login_required
def startinvoice(request):
    pricebands = PriceBand.objects.all()
    ptypes = ProductType.objects.all()
    if request.method == "POST":
        iform = ChooseContactForm(request.POST, prefix="invoice")
        bform = ChooseContactForm(request.POST, prefix="bill")
        if iform.is_valid():
            contacts = xero.get_contacts(iform.cleaned_data['name'])
            if not contacts:
                iform.add_error('name', "No contact exists with this name")
            elif len(contacts) == 1:
                return HttpResponseRedirect(
                    reverse("invoice", args=[contacts[0]["ContactID"]]))
            else:
                return render(request, 'invoicer/multicontact.html',
                              {"contacts": contacts})
        if bform.is_valid():
            contacts = xero.get_contacts(bform.cleaned_data['name'])
            if not contacts:
                bform.add_error('name', "No contact exists with this name")
            elif len(contacts) == 1:
                return HttpResponseRedirect(
                    reverse("bill", args=[contacts[0]["ContactID"]]))
            else:
                return render(request, 'invoicer/multicontact.html',
                              {"contacts": contacts})
    else:
        iform = ChooseContactForm(prefix="invoice")
        bform = ChooseContactForm(prefix="bill")

    return render(request, 'invoicer/startinvoice.html',
                  {"iform": iform,
                   "bform": bform,
                   "bands": pricebands,
                   "ptypes": ptypes})

class ContactOptionsForm(forms.Form):
    priceband = forms.ModelChoiceField(
        queryset=PriceBand.objects,
        label="Price band",
        widget=forms.Select(attrs={"onChange":'javascript: submit()'}),
    )
    account = forms.CharField(max_length=10, required=False,
                              help_text="Overrides accounts shown below")

class _XeroSendFailure(Exception):
    def __init__(self, message):
        self.message = message

def _send_to_xero(contactid, contact_extra, lines, bill):
    products = set()
    invitems = []
    for l in lines:
        il = parse_item(l['item'], exactmatch=True)
        if len(il) != 1:
            raise _XeroSendFailure(
                "Ambiguous invoice item '{}'".format(l))
        item = il[0]
        if not item.product.sent:
            products.add(item.product)
        invitems.append(item)

    if products:
        problem = xero.update_products(products)
        if problem:
            raise _XeroSendFailure("Received {} response when sending product "
                                   "details to Xero".format(problem))
        for p in products:
            p.sent = True
            p.save()

    try:
        invid, warnings = xero.send_invoice(
            contactid, contact_extra.priceband, invitems,
            settings.BILL_ACCOUNT if bill else contact_extra.account, bill)
    except xero.Problem as e:
        raise _XeroSendFailure("Failed sending to Xero: {}".format(
            e.message))
    return invid, warnings

class InvoiceLineForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(InvoiceLineForm, self).__init__(*args, **kwargs)
        self.cp = None
        if "initial" in kwargs and "item" in kwargs['initial']:
            l = parse_item(kwargs['initial']['item'], exactmatch=True)
            if len(l) == 1:
                self.cp = l[0]
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
    def product(self):
        return self.cp.product if self.cp else ""
    def abv(self):
        return str(self.cp.product.abv)+"%" if self.cp else ""
    def barrels(self):
        return self.cp.barrels if self.cp else ""
    def barrelprice(self):
        if self.cp and self.priceband:
            return self.cp[self.priceband].priceperbarrel
        return ""
    def barrelreasons(self):
        if self.cp and self.priceband:
            return self.cp[self.priceband].reasons
        return []
    def totalprice(self):
        if self.cp and self.priceband:
            return self.cp[self.priceband].price
        return ""
    def priceincvat(self):
        if self.cp and self.priceband:
            return self.cp[self.priceband].priceincvat
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

@login_required
def invoice(request, contactid, bill=False):
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
    if bill:
        storename = contactid + "-bill"
    else:
        storename = contactid
    if request.method == "POST":
        cform = ContactOptionsForm(request.POST)
        priceband = None
        if cform.is_valid():
            priceband = cform.cleaned_data['priceband']
        iform = InvoiceLineFormSet(priceband, request.POST,
                                   initial=request.session.get(storename))
        if cform.is_valid() and iform.is_valid():
            if not contact_extra:
                contact_extra = Contact(xero_id=contactid)
            contact_extra.name = contactname
            contact_extra.updated = timezone.now()
            contact_extra.priceband = cform.cleaned_data['priceband']
            contact_extra.account = cform.cleaned_data['account']
            contact_extra.save()
            request.session[storename] = [
                i for i in iform.cleaned_data if not i.get('DELETE',True)]
            if "send" in request.POST or "send-background" in request.POST:
                if not request.session[storename]:
                    messages.warning(request, "There was nothing to send!")
                    return HttpResponseRedirect("")
                try:
                    invid, warnings = _send_to_xero(
                        contactid, contact_extra, request.session[storename],
                        bill)
                    del request.session[storename]
                    iurl = "https://go.xero.com/{}/Edit.aspx?InvoiceID={}".format(
                        "AccountsPayable" if bill else "AccountsReceivable",
                        invid)
                    if warnings:
                        return render(request, 'invoicer/invoicewarnings.html',
                                      {"invid": invid,
                                       "iurl": iurl,
                                       "warnings": warnings})
                    if "send" in request.POST:
                        return HttpResponseRedirect(iurl)
                    messages.success(
                        request,"Invoice for {} sent to Xero".format(contactname))
                    return HttpResponseRedirect(reverse(startinvoice))
                except _XeroSendFailure as e:
                    messages.error(request, e.message)
            return HttpResponseRedirect("")
    else:
        initial = {}
        priceband = None
        if contact_extra:
            priceband = contact_extra.priceband
            initial['priceband'] = priceband
            initial['account'] = contact_extra.account
        cform = ContactOptionsForm(initial=initial)
        iform = InvoiceLineFormSet(
            priceband, initial=request.session.get(storename))
    return render(request, 'invoicer/invoice.html',
                  {"contactname": contactname,
                   "bill": bill,
                   "billaccount": settings.BILL_ACCOUNT,
                   "priceband": priceband,
                   "cform": cform,
                   "iform": iform})

@login_required
def contact_completions(request):
    q = request.GET['q']
    l = xero.get_contacts(q, use_contains=True)
    return JsonResponse([x["Name"] for x in l], safe=False)

class InvoiceItemBand:
    def __init__(self, item, priceband):
        self.priceperbarrel, self.reasons = priceband.price_for(item)
        self.price = (self.priceperbarrel * item.barrels)\
            .quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        self.priceincvat = (self.price * settings.VAT_MULTIPLIER)\
            .quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        
class InvoiceItem:
    def __init__(self, items, unit, product):
        self.items = items
        self.unitname = unit.name
        self.barrelsperitem = unit.size
        self.barrels = unit.size * items
        self.producttype = unit.type
        self.flags = unit.flags
        self.product = product
        self._bands = {}
    def __str__(self):
        return "{} {}{} {}".format(
            self.items, self.unitname, "s" if self.items > 1 else "",
            self.product.name)
    def __getitem__(self, key):
        if key not in self._bands:
            self._bands[key] = InvoiceItemBand(self, key)
        return self._bands[key]

itemre = re.compile(r'^(?P<qty>\d+)\s*(?P<unit>[\w]+?( keg)?)s?\s+(?P<product>[\w\s&-]+)$')
shortre = re.compile(r'^(?P<qty>\d+)\s*(?P<product>[\w\s&-]+)$')

def parse_item(description, exactmatch=False):
    """Convert an item description to a list of InvoiceItem objects
    """
    items = 0
    unitname = ""
    product = ""
    m = itemre.match(description)
    if m:
        items = int(m.group('qty'))
        unitname = m.group('unit')
        product = m.group('product')
    else:
        m = shortre.match(description)
        if m and not exactmatch:
            items = int(m.group('qty'))
            product = m.group('product')
    if items < 1 or len(product) < 2:
        return []
    # Find all matching units
    mu = []
    units = Unit.objects.all()
    for k in units:
        if k.name.startswith(unitname):
            mu.append(k)

    # For each matching unit, search for matching products.  A product
    # matches either on the item code or product name if its type also
    # matches the unit.
    l = []
    if exactmatch:
        productfilter = Q(name=product)
    else:
        productfilter = Q(name__icontains=product) | Q(code__icontains=product)
    for unit in mu:
        products = Product.objects\
                          .filter(type=unit.type)\
                          .filter(productfilter)\
                          .all()
        for p in products:
            l.append(InvoiceItem(items, unit, p))
    l.sort(key=lambda item:item.product.swap)
    # If the product name entered matches (case-insensitive) the
    # product code, sort this to the top
    l.sort(key=lambda item:item.product.code.lower() != product.lower())
    return l

@login_required
def item_completions(request):
    try:
        q = request.GET['q']
    except KeyError:
        return JsonResponse(["No q parameter in request"], safe=False)
    l = parse_item(q)
    return JsonResponse([str(i) for i in l], safe=False)

@login_required
def item_details(request):
    d = {
        'abv': '',
        'barrels': '',
        'barrelprice': '',
        'total': '',
        'incvat': '',
        'account': '',
        'error': '',
        }
    try:
        q = request.GET['q']
        band = int(request.GET['b'])
    except KeyError:
        d['error'] = "Invalid q and/or b parameters in request"
        return JsonResponse(d)
    # band will be the pk - integer
    try:
        priceband = PriceBand.objects.get(pk=band)
    except PriceBand.DoesNotExist:
        d['error'] = "Price band {} does not exist".format(band)
        return JsonResponse(d)
    l = parse_item(q, exactmatch=True)
    if len(l) != 1:
        d['error'] = "Ambiguous invoice line"
        return JsonResponse(d)
    i = l[0]
    d = {
        'abv': "{}%".format(i.product.abv),
        'barrels': i.barrels,
        'barrelprice': render_to_string(
            "invoicer/pricedetail.html",
            {"price": i[priceband].priceperbarrel,
             "reasons": i[priceband].reasons,
             "product": i.product,
            }),
        'total': i[priceband].price,
        'incvat': i[priceband].priceincvat,
        'account': i.product.account,
        'error': "(Not saved)",
    }
    return JsonResponse(d)

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['code', 'name', 'abv', 'type', 'swap']
    def clean(self):
        cleaned_data = super(ProductForm, self).clean()
        code = cleaned_data.get("code")
        # We validate the code if there's no existing product or if
        # the code has changed
        if not (self.instance and code == self.instance.code):
            xero_match = xero.get_product(code)
            if xero_match:
                raise forms.ValidationError(
                    "Code {} already exists in Xero for {}".format(
                        code, xero_match))

@login_required
def product(request, productid=None):
    product = None
    if productid:
        try:
            product = Product.objects.get(pk=int(productid))
        except Product.DoesNotExist:
            raise Http404
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            o = form.save(commit=False)
            if "code" in form.changed_data or "name" in form.changed_data \
               or "abv" in form.changed_data:
                if o.sent:
                    o.sent = False
                    messages.warning(request, "Product will be re-sent to Xero "
                                     "next time it is used in an invoice")
            o.save()
            messages.success(request, "Product updated")
            return HttpResponseRedirect(o.get_absolute_url())
    else:
        form = ProductForm(instance=product)
    # Table has price band across the top, relevant units down the left
    if product:
        bands = PriceBand.objects.all()
        units = [InvoiceItem(1, x, product)
                 for x in Unit.objects.filter(type=product.type).all()]
        # XXX this works around the inability of the Django template system
        # to perform dictionary lookups based on variables
        for u in units:
            u.bandinfo = [u[b] for b in bands]
    else:
        bands = []
        units = []
    return render(request, 'invoicer/product.html',
                  {'product': product, 'form': form,
                   'bands': bands, 'units': units})

@login_required
def productcode_check(request):
    try:
        q = request.GET['q']
        productid = int(request.GET.get('p', 0))
    except:
        return JsonResponse({'ok': False, 'error': 'Bad parameters'})

    product = None
    if productid:
        try:
            product = Product.objects.get(pk=productid)
        except Product.DoesNotExist:
            return JsonResponse(
                {'ok': False,
                 'error': 'Product {} does not exist'.format(productid)})
    if product and q == product.code:
        return JsonResponse(
            {'ok': True,
             'error': 'Unchanged'})
    try:
        np = Product.objects.get(code=q)
        return JsonResponse(
            {'ok': False,
             'error': 'In use for {}'.format(product.name)})
    except Product.DoesNotExist:
        pass
    c = xero.get_product(q)
    if c:
        return JsonResponse(
            {'ok': False,
             'error': 'In use on Xero for {}'.format(c)})
    return JsonResponse({'ok': True, 'error': 'Available'})

@login_required
def productname_check(request):
    try:
        q = request.GET['q']
    except:
        return JsonResponse({'ok': False, 'error': 'Bad parameters'})
    try:
        product = Product.objects.get(name=q)
        return JsonResponse({'ok': False, 'error': 'Already exists'})
    except Product.DoesNotExist:
        pass
    return JsonResponse({'ok': True, 'error': 'Ok'})
