from django.shortcuts import render, redirect
import requests
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2.rfc6749.errors import OAuth2Error
from xml.etree.ElementTree import Element, SubElement, tostring, fromstring
from django.conf import settings
from django.http import Http404
import datetime
import logging
log = logging.getLogger(__name__)

# Zap the very unhelpful behaviour from oauthlib when Xero returns
# more scopes than requested
import os
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = "true"

XERO_ENDPOINT_URL = "https://api.xero.com/api.xro/2.0/"
XERO_AUTHORIZE_URL = "https://login.xero.com/identity/connect/authorize"
XERO_CONNECT_URL = "https://identity.xero.com/connect/token"
XERO_REVOKE_URL = "https://identity.xero.com/connect/revocation"
XERO_CONNECTIONS_URL = "https://api.xero.com/connections"

client_id = settings.XERO_CLIENT_ID
client_secret = settings.XERO_CLIENT_SECRET
tenant_id = settings.XERO_ORGANISATION_ID

token_key = 'xero-token'

def xero_session(request, state=None, omit_tenant=False):
    kwargs = {}
    if token_key in request.session:
        kwargs['token'] = request.session[token_key]
        def token_updater(token):
            nonlocal request
            request.session[token_key] = token
        kwargs['token_updater'] = token_updater
        kwargs['auto_refresh_kwargs'] = {
            'client_id': client_id,
            'client_secret': client_secret,
        }
        kwargs['auto_refresh_url'] = XERO_CONNECT_URL
    if state:
        kwargs['state'] = state

    session = OAuth2Session(
        client_id,
        redirect_uri="http://localhost:8000/xero/callback/" if settings.DEBUG \
        else "https://milton-invoice.assorted.org.uk/xero/callback/",
        scope=["offline_access", "accounting.transactions",
               "accounting.contacts.read", "accounting.settings"],
        **kwargs)

    if not omit_tenant:
        session.headers = {'xero-tenant-id': tenant_id,
                           'accept': 'application/xml',
        }

    return session

def connection_ok(request):
    if token_key not in request.session:
        return False
    session = xero_session(request, omit_tenant=True)
    r = session.get(XERO_CONNECTIONS_URL)
    if r.status_code != 200:
        return False
    connections = r.json()
    for tenant in connections:
        if tenant['tenantId'] == tenant_id:
            return True
    return False

def connect(request):
    xero = xero_session(request, omit_tenant=True)
    authorization_url, state = xero.authorization_url(XERO_AUTHORIZE_URL)
    request.session['xero-auth-state'] = state
    return redirect(authorization_url)

def connect_callback(request):
    xero = xero_session(request, state=request.session['xero-auth-state'],
                        omit_tenant=True)
    try:
        token = xero.fetch_token(
            XERO_CONNECT_URL,
            client_id=client_id,
            client_secret=client_secret,
            authorization_response=request.build_absolute_uri())
        request.session['xero-token'] = token
        return redirect('new-invoice')
    except OAuth2Error as e:
        return render(request, "invoicer/xeroerror.html",
                      context={'error': e})
    return redirect('/')

def disconnect(request):
    xero = xero_session(request, omit_tenant=True)
    r = requests.post(XERO_REVOKE_URL, auth=(client_id, client_secret),
                      data={'token': xero.token['refresh_token']})
    return r.status_code == 200

class Problem(Exception):
    def __init__(self, message):
        self.message = message

def _textelem(name, text):
    e = Element(name)
    e.text = text
    return e

def _fieldtext(c, field):
    f = c.find(field)
    if f is None:
        return
    return f.text

def _contact_to_dict(c):
    return {
        "ContactID": c.find("ContactID").text,
        "Name": c.find("Name").text,
        "FullName": " ".join([_fieldtext(c, "FirstName") or "",
                              _fieldtext(c, "LastName") or ""]),
    }

def get_contacts(request, q, use_contains=False):
    session = xero_session(request)
    if use_contains:
        w = "Name.ToLower().Contains(\"{}\")".format(q.lower())
    else:
        w = "Name.ToLower()==\"{}\"".format(q.lower())
    # w += "&&IsCustomer==true"
    r = session.get(XERO_ENDPOINT_URL + "Contacts/", params={
        "where": w, "order": "Name"})
    if r.status_code != 200:
        log.error("Xero API returned status code %d during get_contacts; text was %s", r.status_code, r.text)
        return []
    root = fromstring(r.text)
    if root.tag != "Response":
        return []
    contacts = root.find("Contacts")
    if not contacts:
        return []
    return [_contact_to_dict(c) for c in contacts.findall("Contact")]

def get_contact(request, contactid):
    session = xero_session(request)
    r = session.get(XERO_ENDPOINT_URL + "Contacts/" + contactid)
    if r.status_code != 200:
        raise Http404
    root = fromstring(r.text)
    if root.tag != "Response":
        return
    c = root.find("./Contacts/Contact")
    if not c:
        return
    d = _contact_to_dict(c)
    bills = c.find("PaymentTerms/Bills")
    if bills:
        d["BillDay"] = int(_fieldtext(bills, "Day"))
        d["BillType"] = _fieldtext(bills, "Type")
    sales = c.find("PaymentTerms/Sales")
    if sales:
        d["SaleDay"] = int(_fieldtext(sales, "Day"))
        d["SaleType"] = _fieldtext(sales, "Type")
    return d

def get_product(request, code):
    session = xero_session(request)
    r = session.get(XERO_ENDPOINT_URL + "Items/" + code)
    if r.status_code != 200:
        return
    root = fromstring(r.text)
    if root.tag != "Response":
        return
    i = root.find("./Items/Item")
    if not i:
        raise Problem("Response did not contain item details")
    desc = _fieldtext(i, "Description")
    return desc

def update_products(request, products):
    session = xero_session(request)
    items = Element("Items")
    for p in products:
        item = Element("Item")
        item.append(_textelem("Code", p.code))
        item.append(_textelem("Name", str(p)))
        item.append(_textelem("Description", str(p)))
        items.append(item)

    xml = tostring(items)
    r = session.post(XERO_ENDPOINT_URL + "Items/",
                      data={'xml': xml})
    if r.status_code != 200:
        log.error("%s", r.text)
        return r.status_code

def send_invoice(request, contactid, priceband, items,
                 bill, date, duedate, reference):
    session = xero_session(request)
    # items is a list of (item, gyle) tuples
    invoices = Element("Invoices")
    inv = SubElement(invoices, "Invoice")
    inv.append(_textelem("Type", "ACCPAY" if bill else "ACCREC"))
    c = SubElement(inv, "Contact")
    c.append(_textelem("ContactID", contactid))
    inv.append(_textelem(
        "LineAmountTypes", "Exclusive"))
    inv.append(_textelem(
        "Date", date.isoformat()))
    if duedate:
        inv.append(_textelem(
            "DueDate", duedate.isoformat()))
    if reference:
        if bill:
            inv.append(_textelem("InvoiceNumber", reference))
        else:
            inv.append(_textelem("Reference", reference))
    litems = SubElement(inv, "LineItems")
    for i, gyle in items:
        li = SubElement(litems, "LineItem")
        desc = "{} ({}% ABV)".format(i, i.product.abv)
        if gyle:
            desc += " (gyle {})".format(gyle)
        li.append(_textelem("Description", desc))
        li.append(_textelem("ItemCode", i.product.code))
        li.append(_textelem("Quantity", str(i.barrels)))
        li.append(_textelem("AccountCode", i[priceband].account))
        li.append(_textelem("UnitAmount", str(i[priceband].priceperbarrel)))
    xml = tostring(invoices)
    r = session.put(XERO_ENDPOINT_URL + "Invoices/",
                     data={'xml': xml})
    if r.status_code == 400:
        root = fromstring(r.text)
        messages = [e.text for e in root.findall(".//Message")]
        raise Problem("Xero rejected invoice: {}".format(", ".join(messages)))
    if r.status_code != 200:
        raise Problem("Received {} response".format(r.status_code))
    root = fromstring(r.text)
    if root.tag != "Response":
        raise Problem("Response root tag '{}' was not 'Response'".format(
            root.tag))
    i = root.find("./Invoices/Invoice")
    if not i:
        raise Problem("Response did not contain invoice details")
    invid = _fieldtext(i, "InvoiceID")
    if not invid:
        raise Problem("No invoice ID was returned")
    warnings = [w.text for w in i.findall("./Warnings/Warning/Message")]
    return invid, warnings

def test_connection(request):
    """Test the connection to Xero by retrieving organisation name"""
    session = xero_session(request)
    r = session.get(XERO_ENDPOINT_URL + "Organisation/")
    if r.status_code != 200:
        return "Connection failed: status code {}".format(r.status_code)
    root = fromstring(r.text)
    if root.tag != "Response":
        return "Connection failed: root of response was not 'Response'."
    org = None
    orgs = root.find("Organisations")
    if orgs is not None:
        org = orgs.find("Organisation")
    if org is None:
        return "Connection failed: no organisation details in response"
    return _fieldtext(org, "Name")
