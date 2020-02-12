# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('invoicer', '0008_product_sent'),
    ]

    operations = [
        migrations.CreateModel(
            name='Unit',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', auto_created=True, serialize=False)),
                ('name', models.CharField(help_text='Unit names with spaces in may require code changes to work', max_length=10)),
                ('size', models.DecimalField(max_digits=5, help_text='Size in barrels', decimal_places=4)),
                ('flags', models.CharField(blank=True, max_length=50)),
                ('type', models.ForeignKey(to='invoicer.ProductType', on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
