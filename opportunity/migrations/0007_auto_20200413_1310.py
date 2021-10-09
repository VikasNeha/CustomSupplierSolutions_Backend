# Generated by Django 2.2.12 on 2020-04-13 13:10

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('opportunity', '0006_auto_20200410_1805'),
    ]

    operations = [
        migrations.CreateModel(
            name='State',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=2, unique=True, verbose_name='StateCode')),
                ('name', models.CharField(max_length=50, unique=True, verbose_name='State')),
            ],
        ),
        migrations.CreateModel(
            name='City',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='City')),
                ('state', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='opportunity.State', verbose_name='State')),
            ],
        ),
        migrations.AddField(
            model_name='opportunitylisting',
            name='cities',
            field=models.ManyToManyField(null=True, to='opportunity.City'),
        ),
        migrations.AddField(
            model_name='opportunitylisting',
            name='states',
            field=models.ManyToManyField(null=True, to='opportunity.State'),
        ),
    ]
