from django.core.management.base import BaseCommand, CommandError
from invoicer.models import *
import csv

suffixes = ("1", "2", "3", "4", "swap", "pin", "polypin", "poly", )

class Command(BaseCommand):
    args = 'filename.csv'
    help = 'Import CSV file of products'
    def handle(self, *args, **options):
        filename=args[0]
        cask = ProductType.objects.get(name="Cask ale")
        with open(filename, encoding='iso-8859-1') as f:
            reader = csv.DictReader(f, quotechar="'")
            for r in reader:
                if r["Sell"] != "S" or not r["Sell Unit Measure"]:
                    print("Skipping {}".format(r['Item Name']))
                    continue
                item = r['Item Number'].strip()
                name = r['Item Name'].strip()
                if not name:
                    print("Skipping - blank name")
                    continue
                if not item:
                    print("Skipping - blank item code")
                    continue
                try:
                    abv = Decimal(r['Sell Unit Measure'].strip())
                except:
                    print("Skipping {} - couldn't read ABV".format(name))
                    continue
                if abv < Decimal("2.5"):
                    print("Skipping {} - low ABV".format(name))
                    continue
                if "brewers disc" in name:
                    print("Skipping {} - brewers discount item".format(name))
                    continue
                # Check for common suffixes and remove them:
                for s in suffixes:
                    if len(item) <= len(s):
                        continue
                    if item[-len(s):].lower() == s:
                        item = item[:-len(s)].strip()
                # Do we already have this item code?
                p = None
                try:
                    p = Product.objects.get(code=item)
                except Product.DoesNotExist:
                    pass
                if not p:
                    try:
                        p = Product.objects.get(name=name)
                    except Product.DoesNotExist:
                        pass
                if not p:
                    # New item!  Create it.
                    p = Product(
                        name=name, code=item, abv=abv, type=cask,
                        swap=' ' in name)
                    p.save()
                else:
                    if p.name!=name or p.abv!=abv or p.code!=item:
                        print("Mismatch on {} - not updating".format(name))
