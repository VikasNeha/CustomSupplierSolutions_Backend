# Generated by Django 2.2.12 on 2020-09-28 14:55

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('opportunity', '0018_productservicecategory_code'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='opportunitylisting',
            name='psc_code',
        ),
    ]
