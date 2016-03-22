# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('invoicer', '0006_auto_20160321_2052'),
    ]

    operations = [
        migrations.RenameField(
            model_name='contact',
            old_name='default_priceband',
            new_name='priceband',
        ),
    ]
