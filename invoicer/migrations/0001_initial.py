# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ConfigOption',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True, serialize=False)),
                ('name', models.CharField(max_length=40)),
                ('value', models.CharField(max_length=80)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Contact',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True, serialize=False)),
                ('name', models.CharField(max_length=500)),
                ('xero_id', models.CharField(unique=True, max_length=36)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Price',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True, serialize=False)),
                ('abv', models.DecimalField(max_digits=3, decimal_places=1)),
                ('price', models.DecimalField(max_digits=6, decimal_places=2)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='PriceBand',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True, serialize=False)),
                ('name', models.CharField(max_length=40)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='PriceOverride',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True, serialize=False)),
                ('price', models.DecimalField(max_digits=6, decimal_places=2)),
                ('band', models.ForeignKey(to='invoicer.PriceBand', on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True, serialize=False)),
                ('name', models.CharField(max_length=80)),
                ('abv', models.DecimalField(max_digits=3, decimal_places=1)),
                ('xero_code', models.CharField(unique=True, max_length=30)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ProductType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True, serialize=False)),
                ('name', models.CharField(max_length=80)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='product',
            name='type',
            field=models.ForeignKey(to='invoicer.ProductType', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='priceoverride',
            name='product',
            field=models.ForeignKey(to='invoicer.Product', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='price',
            name='band',
            field=models.ForeignKey(to='invoicer.PriceBand', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='price',
            name='type',
            field=models.ForeignKey(to='invoicer.ProductType', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='price',
            unique_together=set([('band', 'type', 'abv')]),
        ),
        migrations.AddField(
            model_name='contact',
            name='default_priceband',
            field=models.ForeignKey(to='invoicer.PriceBand', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='configoption',
            name='band',
            field=models.ForeignKey(to='invoicer.PriceBand', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='configoption',
            unique_together=set([('band', 'name')]),
        ),
    ]
