# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('invoicer', '0013_auto_20160424_1307'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='price',
            options={'ordering': ['priority']},
        ),
    ]
