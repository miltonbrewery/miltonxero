# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('invoicer', '0005_contact_updated'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='product',
            options={'ordering': ['name']},
        ),
        migrations.RenameField(
            model_name='priceoverride',
            old_name='price',
            new_name='pricechange',
        ),
        migrations.AlterField(
            model_name='priceband',
            name='name',
            field=models.CharField(max_length=40, unique=True),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='priceoverride',
            unique_together=set([('band', 'product')]),
        ),
    ]
