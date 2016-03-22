# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('invoicer', '0004_contact_account'),
    ]

    operations = [
        migrations.AddField(
            model_name='contact',
            name='updated',
            field=models.DateTimeField(default=datetime.datetime(2016, 3, 21, 16, 47, 48, 754427)),
            preserve_default=False,
        ),
    ]
