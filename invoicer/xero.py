import requests
from oauthlib.oauth1 import SIGNATURE_RSA, SIGNATURE_TYPE_AUTH_HEADER, SIGNATURE_HMAC
from requests_oauthlib import OAuth1
from xml.etree.ElementTree import Element, SubElement, tostring, fromstring
from django.conf import settings
from django.http import Http404
import datetime

XERO_ENDPOINT_URL = "https://api.xero.com/api.xro/2.0/"

oauth = OAuth1(
    settings.XERO_CONSUMER_KEY,
    resource_owner_key=settings.XERO_CONSUMER_KEY,
    rsa_key=settings.XERO_PRIVATE_KEY,
    signature_method=SIGNATURE_RSA,
    signature_type=SIGNATURE_TYPE_AUTH_HEADER)

def _textelem(name, text):
    e = Element(name)
    e.text = text
    return e

def send_session_totals(api, session, contact, reference=None,
                        differences_account=None):
    """Send session totals to Xero

    session is a models.Session instance.  Returns a string describing
    what happened.
    """
    if not session.endtime:
        return "Session isn't closed!  Could not send."

    invoices = Element("Invoices")
    inv = SubElement(invoices, "Invoice")
    inv.append(_textelem("Type", "ACCREC"))
    c = SubElement(inv, "Contact")
    c.append(_textelem("Name", contact))
    inv.append(_textelem("Date", session.date.isoformat()))
    inv.append(_textelem(
        "DueDate", (session.date + datetime.timedelta(days=4)).isoformat()))
    if reference:
        inv.append(_textelem("Reference", reference))
    inv.append(_textelem(
        "LineAmountTypes", "Inclusive"))
    litems = SubElement(inv, "LineItems")
    for dept, total in session.dept_totals:
        extras = fromstring("<e>{}</e>".format(dept.accinfo))
        li = SubElement(litems, "LineItem")
        li.append(_textelem("Description", dept.description + " sales"))
        li.append(_textelem("Quantity", "1.00"))
        li.append(_textelem("UnitAmount", unicode(total)))
        for sub in extras:
            li.append(sub)
            xml = tostring(invoices)

    #if differences_account:
    #    li = SubElement(litems, "LineItem")
    #    li.append(_textelem("Description", "
    
    log.debug("XML to send: {}".format(xml))
    r = requests.put(XERO_ENDPOINT_URL + "Invoices/",
                     data={'xml': xml},
                     auth=oauth)
    log.debug("Response: {}".format(r))
    log.debug("Response data: {}".format(r.text))
    return "Session {} sent to Xero: response code {}".format(
        session.id, r.status_code)

def _fieldtext(c, field):
    f = c.find(field)
    if not f:
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
