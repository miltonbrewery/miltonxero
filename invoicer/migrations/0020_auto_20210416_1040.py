# Generated by Django 3.0.14 on 2021-04-16 09:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('invoicer', '0019_auto_20190314_1211'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contact',
            name='notes',
            field=models.CharField(blank=True, default='', max_length=500),
        ),
    ]
