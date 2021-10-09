# Generated by Django 2.2.12 on 2021-02-22 14:14

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('opportunity', '0025_auto_20201029_1411'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserFilter',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('friendly_name', models.CharField(max_length=100, verbose_name='Friendly Name')),
                ('searchterm', models.CharField(blank=True, max_length=100, null=True, verbose_name='Search Term')),
                ('posting_date_start', models.DateField(blank=True, null=True, verbose_name='Posting Date Start')),
                ('posting_date_end', models.DateField(blank=True, null=True, verbose_name='Posting Date End')),
                ('due_date_start', models.DateField(blank=True, null=True, verbose_name='Due Date Start')),
                ('due_date_end', models.DateField(blank=True, null=True, verbose_name='Due Date End')),
                ('created_date', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('updated_date', models.DateTimeField(auto_now=True, verbose_name='Updated At')),
                ('buyer', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='opportunity.BuyerListing', verbose_name='Deptt/Agency')),
                ('naics_code', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='opportunity.NAICSCode', verbose_name='NAICS Code')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'User Filter',
                'verbose_name_plural': 'User Filters',
                'unique_together': {('user', 'friendly_name')},
            },
        ),
    ]
