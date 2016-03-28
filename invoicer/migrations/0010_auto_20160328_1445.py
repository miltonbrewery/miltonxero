# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('invoicer', '0009_unit'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='sent',
            field=models.BooleanField(help_text='Has this product code been sent to Xero yet?', default=False),
            preserve_default=True,
        ),
    ]
