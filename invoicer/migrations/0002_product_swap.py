# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('invoicer', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='swap',
            field=models.BooleanField(default=True),
            preserve_default=True,
        ),
    ]
