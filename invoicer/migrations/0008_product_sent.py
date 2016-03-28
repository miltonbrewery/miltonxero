# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('invoicer', '0007_auto_20160322_0956'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='sent',
            field=models.BooleanField(help_text='Has this product codebeen sent to Xero yet?', default=False),
            preserve_default=True,
        ),
    ]
