# Generated by Django 2.2.12 on 2020-04-13 13:19

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('opportunity', '0009_auto_20200413_1316'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='opportunitylisting',
            name='city',
        ),
        migrations.RemoveField(
            model_name='opportunitylisting',
            name='state',
        ),
    ]