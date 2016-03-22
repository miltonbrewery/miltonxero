# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('invoicer', '0002_product_swap'),
    ]

    operations = [
        migrations.RenameField(
            model_name='product',
            old_name='xero_code',
            new_name='code',
        ),
        migrations.AlterField(
            model_name='product',
            name='name',
            field=models.CharField(unique=True, max_length=80),
            preserve_default=True,
        ),
    ]
