import requests
from oauthlib.oauth1 import SIGNATURE_RSA, SIGNATURE_TYPE_AUTH_HEADER, SIGNATURE_HMAC
from requests_oauthlib import OAuth1
from xml.etree.ElementTree import Element, SubElement, tostring, fromstring
from django.conf import settings
from django.http import Http404
import datetime
import logging
log = logging.getLogger(__name__)

XERO_ENDPOINT_URL = "https://api.xero.com/api.xro/2.0/"

oauth = OAuth1(
    settings.XERO_CONSUMER_KEY,
    resource_owner_key=settings.XERO_CONSUMER_KEY,
    rsa_key=settings.XERO_PRIVATE_KEY,
    signature_method=SIGNATURE_RSA,
    signature_type=SIGNATURE_TYPE_AUTH_HEADER)

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

def get_contacts(q, use_contains=False):
    if use_contains:
        w = "Name.ToLower().Contains(\"{}\")".format(q.lower())
    else:
        w = "Name.ToLower()==\"{}\"".format(q.lower())
    # w += "&&IsCustomer==true"
    r = requests.get(XERO_ENDPOINT_URL + "Contacts/", params={
        "where": w, "order": "Name"}, auth=oauth)
    if r.status_code != 200:
        return []
    root = fromstring(r.text)
    if root.tag != "Response":
        return []
    contacts = root.find("Contacts")
    if not contacts:
        return []
    return [_contact_to_dict(c) for c in contacts.findall("Contact")]

def get_contact(contactid):
    r = requests.get(XERO_ENDPOINT_URL + "Contacts/" + contactid,
                     auth=oauth)
    if r.status_code != 200:
        raise Http404
    root = fromstring(r.text)
    if root.tag != "Response":
        return
    c = root.find("./Contacts/Contact")
    if not c:
        return
    return _contact_to_dict(c)

def get_product(code):
    r = requests.get(XERO_ENDPOINT_URL + "Items/" + code, auth=oauth)
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

def update_products(products):
    items = Element("Items")
    for p in products:
        item = Element("Item")
        item.append(_textelem("Code", p.code))
        item.append(_textelem("Name", str(p)))
        item.append(_textelem("Description", str(p)))
        items.append(item)

    xml = tostring(items)
    r = requests.post(XERO_ENDPOINT_URL + "Items/",
                      data={'xml': xml},
                      auth=oauth)
    if r.status_code != 200:
        log.error("%s", r.text)
        return r.status_code

def send_invoice(contactid, priceband, items, bill):
    invoices = Element("Invoices")
    inv = SubElement(invoices, "Invoice")
    inv.append(_textelem("Type", "ACCPAY" if bill else "ACCREC"))
    c = SubElement(inv, "Contact")
    c.append(_textelem("ContactID", contactid))
    inv.append(_textelem(
        "LineAmountTypes", "Exclusive"))
    inv.append(_textelem(
        "Date", datetime.date.today().isoformat()))
    inv.append(_textelem(
        "DueDate", (datetime.date.today()+datetime.timedelta(days=31)).isoformat()))
    litems = SubElement(inv, "LineItems")
    for i in items:
        li = SubElement(litems, "LineItem")
        li.append(_textelem("Description",
                            str(i) + " ({}% ABV)".format(i.product.abv)))
        li.append(_textelem("ItemCode", i.product.code))
        li.append(_textelem("Quantity", str(i.barrels)))
        li.append(_textelem("AccountCode", i[priceband].account))
        li.append(_textelem("UnitAmount", str(i[priceband].priceperbarrel)))
    xml = tostring(invoices)
    r = requests.put(XERO_ENDPOINT_URL + "Invoices/",
                     data={'xml': xml},
                     auth=oauth)
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
