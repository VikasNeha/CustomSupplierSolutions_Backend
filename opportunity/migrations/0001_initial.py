# Generated by Django 2.2.12 on 2020-04-09 12:55

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='BuyerListing',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('website', models.CharField(max_length=100, verbose_name='Website')),
                ('buyer_name', models.CharField(max_length=1000, verbose_name='Buyer Name')),
                ('buyer_url', models.URLField(blank=True, max_length=1000, null=True, verbose_name='Buyer URL')),
                ('created_date', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('updated_date', models.DateTimeField(auto_now=True, verbose_name='Updated At')),
            ],
            options={
                'verbose_name': 'Buyer',
                'verbose_name_plural': 'Buyers',
            },
        ),
        migrations.CreateModel(
            name='ProductServiceCategory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('category_name', models.CharField(max_length=200, unique=True, verbose_name='Product/Service Category')),
            ],
        ),
        migrations.CreateModel(
            name='ShiptoServiceLocation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('location_name', models.CharField(max_length=200, unique=True, verbose_name='Location')),
            ],
        ),
        migrations.CreateModel(
            name='OpportunityListing',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('website', models.CharField(max_length=100, verbose_name='Website')),
                ('title', models.CharField(max_length=1000, verbose_name='Title')),
                ('posting_date', models.DateTimeField(blank=True, null=True, verbose_name='Posting Date')),
                ('bidding_open_date', models.DateTimeField(blank=True, null=True, verbose_name='Bidding Open Date')),
                ('submission_deadline', models.DateTimeField(blank=True, null=True, verbose_name='Submission Deadline')),
                ('opprtunity_amount', models.CharField(blank=True, max_length=200, null=True, verbose_name='Opportunity Amount')),
                ('contract_length', models.CharField(blank=True, max_length=200, null=True, verbose_name='Contract Length')),
                ('posting_id', models.CharField(blank=True, max_length=200, null=True, verbose_name='Posting ID')),
                ('posting_type', models.CharField(blank=True, max_length=200, null=True, verbose_name='Posting Type')),
                ('posting_url', models.URLField(blank=True, max_length=1000, null=True, verbose_name='Posting URL')),
                ('posting_summary', models.TextField(blank=True, null=True, verbose_name='Posting Summary')),
                ('created_date', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('updated_date', models.DateTimeField(auto_now=True, verbose_name='Updated At')),
                ('buyer', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='opportunity.BuyerListing')),
                ('product_service_categories', models.ManyToManyField(blank=True, null=True, to='opportunity.ProductServiceCategory', verbose_name='Product and Service Categories')),
                ('shipto_service_locations', models.ManyToManyField(blank=True, null=True, to='opportunity.ShiptoServiceLocation', verbose_name='Ship-to or Service Locations')),
            ],
            options={
                'verbose_name': 'Opprtunity Listing',
                'verbose_name_plural': 'Opprtunities Listings',
            },
        ),
    ]