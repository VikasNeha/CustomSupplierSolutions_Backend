# Generated by Django 2.2.12 on 2020-04-16 13:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('opportunity', '0010_auto_20200413_1319'),
    ]

    operations = [
        migrations.CreateModel(
            name='BusinessType',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('business_type', models.CharField(max_length=1000, unique=True, verbose_name='Business Type')),
            ],
        ),
        migrations.AddField(
            model_name='buyerlisting',
            name='duns',
            field=models.CharField(blank=True, max_length=50, null=True, verbose_name='DUNS'),
        ),
        migrations.AlterField(
            model_name='listingattachment',
            name='attachment',
            field=models.FileField(max_length=500, upload_to='uploads/%Y/%m/%d/', verbose_name='Attachment'),
        ),
        migrations.AddField(
            model_name='opportunitylisting',
            name='business_types_solicited',
            field=models.ManyToManyField(blank=True, to='opportunity.BusinessType'),
        ),
    ]