from django.core.management.base import BaseCommand, CommandError
from invoicer import xero

class Command(BaseCommand):
    help = 'Test connection to Xero'
    def handle(self, *args, **options):
        print(xero.test_connection())
