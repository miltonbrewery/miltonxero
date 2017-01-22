# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('invoicer', '0014_auto_20160424_1727'),
    ]

    operations = [
        migrations.AddField(
            model_name='contact',
            name='suppress_due_date',
            field=models.BooleanField(default=False),
        ),
    ]
