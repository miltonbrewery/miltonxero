# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('invoicer', '0012_data'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='configoption',
            unique_together=None,
        ),
        migrations.RemoveField(
            model_name='configoption',
            name='band',
        ),
        migrations.DeleteModel(
            name='ConfigOption',
        ),
        migrations.AlterUniqueTogether(
            name='priceoverride',
            unique_together=None,
        ),
        migrations.RemoveField(
            model_name='priceoverride',
            name='band',
        ),
        migrations.RemoveField(
            model_name='priceoverride',
            name='product',
        ),
        migrations.DeleteModel(
            name='PriceOverride',
        ),
        migrations.RemoveField(
            model_name='contact',
            name='account',
        ),
        migrations.RemoveField(
            model_name='unit',
            name='flags',
        ),
    ]
