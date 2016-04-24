# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('invoicer', '0010_auto_20160328_1445'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProgramRule',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, auto_created=True, verbose_name='ID')),
                ('name', models.CharField(unique=True, max_length=80)),
                ('code', models.CharField(max_length=20)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='price',
            name='absolute_price',
            field=models.DecimalField(help_text='The new price per barrel when this rule is applied, ignoring prices set by any previous rules', null=True, decimal_places=2, max_digits=6, blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='price',
            name='account',
            field=models.CharField(help_text='The value to use for the Xero account when this rule is applied', max_length=10, blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='price',
            name='comment',
            field=models.CharField(max_length=80, blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='price',
            name='contact',
            field=models.ForeignKey(to='invoicer.Contact', blank=True, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='price',
            name='isBill',
            field=models.NullBooleanField(help_text="Match on whether we are preparing an invoice or a bill; 'Unknown' matches either way"),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='price',
            name='isSwap',
            field=models.NullBooleanField(help_text="Match on whether the product has the 'swap' tickbox set; 'Unknown' matches either way"),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='price',
            name='priority',
            field=models.IntegerField(help_text='Rules are applied in order of priority, with higher values being applied later', default=100),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='price',
            name='product',
            field=models.ForeignKey(to='invoicer.Product', blank=True, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='price',
            name='rule',
            field=models.ForeignKey(to='invoicer.ProgramRule', blank=True, help_text='A programmed rule to alter the price and/or account', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='price',
            name='unit',
            field=models.ForeignKey(to='invoicer.Unit', blank=True, null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='price',
            name='abv',
            field=models.DecimalField(null=True, decimal_places=1, max_digits=3, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='price',
            name='band',
            field=models.ForeignKey(to='invoicer.PriceBand', blank=True, null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='price',
            name='price',
            field=models.DecimalField(help_text='The amount to increase the price per barrel when this rule is applied', null=True, decimal_places=2, max_digits=6, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='price',
            name='type',
            field=models.ForeignKey(to='invoicer.ProductType', blank=True, null=True),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='price',
            unique_together=set([]),
        ),
    ]
