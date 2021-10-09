import os

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex
from django.db import models
from django.utils.html import format_html


class BuyerListing(models.Model):
    website = models.CharField(max_length=100, verbose_name='Website')
    buyer_name = models.CharField(max_length=1000, verbose_name='Buyer Name')
    buyer_url = models.URLField(max_length=1000, verbose_name='Buyer URL', blank=True, null=True)
    duns = models.CharField(max_length=50, verbose_name='DUNS', blank=True, null=True)
    buyer_website_id = models.CharField(max_length=500, verbose_name='Buyer Website ID', blank=True, null=True)
    agency_type = models.CharField(max_length=100, verbose_name='Agency Type', blank=True, null=True)

    created_date = models.DateTimeField(verbose_name='Created At', auto_now_add=True)
    updated_date = models.DateTimeField(verbose_name='Updated At', auto_now=True)

    def __str__(self):
        return self.buyer_name

    class Meta:
        verbose_name = 'Buyer'
        verbose_name_plural = 'Buyers'


class ProductServiceCategory(models.Model):
    code = models.CharField(max_length=10, verbose_name='PSC Code', blank=True, null=True)
    title = models.CharField(max_length=200, verbose_name='Product/Service Category', unique=True)

    def __str__(self):
        return self.title


class ShiptoServiceLocation(models.Model):
    location_name = models.CharField(max_length=200, verbose_name='Location', unique=True)

    def __str__(self):
        return self.location_name


class NAICSCode(models.Model):
    code = models.CharField(max_length=10, verbose_name='NAICS Code', unique=True)
    title = models.CharField(max_length=500, verbose_name='NAICS Title', blank=True, null=True)

    def __str__(self):
        return '{}: {}'.format(self.code, self.title)

    @property
    def get_formatted(self):
        return f'{self.code}: {self.title}'


class NIGPCode(models.Model):
    code = models.CharField(max_length=10, verbose_name='NIGP Code', unique=True)
    title = models.CharField(max_length=500, verbose_name='NIGP Title', blank=True, null=True)

    def __str__(self):
        return '{}: {}'.format(self.code, self.title)


class SetAsideCode(models.Model):
    code = models.CharField(max_length=10, verbose_name='Set Aside Code', unique=True)
    title = models.CharField(max_length=500, verbose_name='Set Aside Title', blank=True, null=True)

    def __str__(self):
        return '{}: {}'.format(self.code, self.title)


class SamGovPSCCode(models.Model):
    code = models.CharField(max_length=10, verbose_name='SAM.GOV PSC Code', unique=True)
    title = models.CharField(max_length=500, verbose_name='SAM.GOV PSC Title', blank=True, null=True)

    def __str__(self):
        return '{}: {}'.format(self.code, self.title)


class Contact(models.Model):
    name = models.TextField(verbose_name='Name', blank=True, null=True)
    email = models.CharField(max_length=200, verbose_name='Email', blank=True, null=True)
    phone = models.CharField(max_length=200, verbose_name='Phone', blank=True, null=True)


class State(models.Model):
    code = models.CharField(max_length=2, verbose_name='StateCode', unique=True)
    name = models.CharField(max_length=50, verbose_name='State', unique=True, blank=True, null=True)

    def __str__(self):
        return self.code


class City(models.Model):
    name = models.CharField(max_length=100, verbose_name='City')
    state = models.ForeignKey(State, verbose_name='State', blank=True, null=True, on_delete=models.DO_NOTHING)

    class Meta:
        unique_together = ('name', 'state')

    def __str__(self):
        return '{}, {}'.format(self.name, self.state.code) if self.state else self.name

    @property
    def state_repr(self):
        return self.state.code


class BusinessType(models.Model):
    business_type = models.CharField(max_length=1000, verbose_name='Business Type', unique=True)

    def __str__(self):
        return self.business_type


class OpportunityListing(models.Model):
    website = models.CharField(max_length=100, verbose_name='Website')
    title = models.CharField(max_length=1000, verbose_name='Title')
    buyer = models.ForeignKey(BuyerListing, on_delete=models.DO_NOTHING, blank=True, null=True,
                              verbose_name='Deptt/Agency')
    posting_date = models.DateTimeField(verbose_name='Posting Date', blank=True, null=True)
    bidding_open_date = models.DateTimeField(verbose_name='Bidding Open Date', blank=True, null=True)
    submission_deadline = models.DateTimeField(verbose_name='Submission Deadline', blank=True, null=True)
    is_deadline_ongoing = models.BooleanField(verbose_name='Is Deadline Ongoing?', default=False)
    opportunity_amount = models.CharField(max_length=200, verbose_name='Opportunity Amount', blank=True, null=True)
    contract_length = models.CharField(max_length=200, verbose_name='Contract Length', blank=True, null=True)
    contract_start_date = models.DateTimeField(verbose_name='Contract Start Date', blank=True, null=True)
    posting_id = models.CharField(max_length=200, verbose_name='Posting ID', blank=True, null=True)
    posting_type = models.CharField(max_length=200, verbose_name='Posting Type', blank=True, null=True)
    posting_url = models.URLField(max_length=1000, verbose_name='Posting URL', blank=True, null=True)
    product_service_categories = models.ManyToManyField(
        ProductServiceCategory, verbose_name='Product and Service Categories', blank=True)
    shipto_service_locations = models.ManyToManyField(
        ShiptoServiceLocation, verbose_name='Ship-to or Service Locations', blank=True)
    location = models.CharField(max_length=1000, verbose_name='Location', blank=True, null=True)
    posting_summary = models.TextField(verbose_name='Posting Summary', blank=True, null=True)
    pre_submission_meeting = models.DateTimeField(verbose_name='Pre-Offer Conference/Pre-Submittal Meeting',
                                                  blank=True, null=True)
    opportunity_type = models.CharField(max_length=500, verbose_name='Opportunity Type', blank=True, null=True)
    set_aside_type = models.CharField(max_length=500, verbose_name='Set Aside Type', blank=True, null=True)
    solicitation_number = models.CharField(max_length=500, verbose_name='Solicitation Number', blank=True, null=True)

    naics_codes = models.ManyToManyField(NAICSCode, verbose_name='NAICS Codes', blank=True)
    nigp_codes = models.ManyToManyField(NIGPCode, verbose_name='NIGP Codes', blank=True)
    contact = models.ForeignKey(Contact, verbose_name='Contact', blank=True, null=True, on_delete=models.DO_NOTHING)

    contacts = models.ManyToManyField(Contact, blank=True, through='OpportunityContact', related_name='Contacts')

    cities = models.ManyToManyField(City, blank=True)
    states = models.ManyToManyField(State, blank=True)
    business_types_solicited = models.ManyToManyField(BusinessType, blank=True)

    search_vector = SearchVectorField(null=True, blank=True)

    created_date = models.DateTimeField(verbose_name='Created At', auto_now_add=True)
    updated_date = models.DateTimeField(verbose_name='Updated At', auto_now=True)

    def __str__(self):
        return '{}: {}'.format(self.website, self.title)

    class Meta:
        verbose_name = 'Opprtunity Listing'
        verbose_name_plural = 'Opprtunities Listings'
        indexes = [GinIndex(fields=['search_vector'])]

    def get_posting_summary(self):
        return format_html(self.posting_summary)
    get_posting_summary.short_description = 'Posting Summary'

    def get_posting_date(self):
        return self.posting_date.date() if self.posting_date else None
    get_posting_date.short_description = 'Posting Date'

    def get_bidding_open_date(self):
        if not self.bidding_open_date:
            return None
        return self.bidding_open_date.date()
    get_bidding_open_date.short_description = 'Bidding Open Date'

    def get_posting_url(self):
        return format_html('<a href="{}" target="_blank">{}</a>', self.posting_url, self.posting_url)
    get_posting_url.short_description = 'Posting Link'

    def get_product_service_categories_admin(self):
        count = self.product_service_categories.count()
        if count == 0:
            return None
        elif count == 1:
            return self.product_service_categories.first()
        html = '<ul>'
        for productservicecategory in self.product_service_categories.all():
            html += '<li>{}</li>'.format(productservicecategory.title)
        html += '</ul>'
        return format_html(html)
    get_product_service_categories_admin.short_description = 'Product and Service Categories'

    def get_shipto_service_locations_admin(self):
        count = self.shipto_service_locations.count()
        if count == 0:
            return None
        elif count == 1:
            return self.shipto_service_locations.first()
        html = '<ul>'
        for shiptoservicelocation in self.shipto_service_locations.all().order_by('location_name'):
            html += '<li>{}</li>'.format(shiptoservicelocation.location_name)
        html += '</ul>'
        return format_html(html)
    get_shipto_service_locations_admin.short_description = 'Ship-to or Service Locations'

    def get_naics_codes(self):
        count = self.naics_codes.count()
        if count == 0:
            return None
        elif count == 1:
            return self.naics_codes.first()
        html = '<ul>'
        for naicscode in self.naics_codes.all().order_by('code'):
            html += '<li>{}: {}</li>'.format(naicscode.code, naicscode.title)
        html += '</ul>'
        return format_html(html)
    get_naics_codes.short_description = 'NAICS Codes'

    def get_nigp_codes(self):
        count = self.nigp_codes.count()
        if count == 0:
            return None
        elif count == 1:
            return self.nigp_codes.first()
        html = '<ul>'
        for nigpcode in self.nigp_codes.all().order_by('code'):
            html += '<li>{}: {}</li>'.format(nigpcode.code, nigpcode.title)
        html += '</ul>'
        return format_html(html)
    get_nigp_codes.short_description = 'NIGP Codes'

    def get_contact(self):
        if self.website in ['GOVTRIBE.COM', 'SAM.GOV']:
            if not self.opportunitycontact_set.exists():
                return None
            html = """<style>
                #contacts {{
                  border-collapse: collapse;
                  width: 100%;
                }}
                
                #contacts td, #contacts th {{
                  border: 1px solid #ddd;
                  padding: 8px;
                }}
                
                #contacts tr:nth-child(even){{background-color: #f2f2f2;}}
                
                #contacts tr:hover {{background-color: #ddd;}}
                
                #contacts th {{
                  padding-top: 12px;
                  padding-bottom: 12px;
                  text-align: left;
                  background-color: #4CAF50;
                  color: white;
                }}
                </style>"""
            html += '<table id="contacts"><tbody><tr><th>Name</th><th>Position</th><th>Email</th><th>Phone</th></tr>'
            for opportunitycontact in self.opportunitycontact_set.all():
                html += f'<tr><td>{opportunitycontact.contact.name}</td><td>{opportunitycontact.position}</td><td>{opportunitycontact.contact.email}</td><td>{opportunitycontact.contact.phone}</td></tr>'
            html += '</tbody></table>'
        else:
            if not self.contact:
                return None
            html = '<b>Name</b>: {}</br><b>Phone</b>: {}</br><b>Email</b>: {}'.format(self.contact.name, self.contact.email, self.contact.phone)
        return format_html(html)
    get_contact.short_description = 'Contact'

    def get_cities(self):
        count = self.cities.count()
        if count == 0:
            return None
        elif count == 1:
            return self.cities.first()
        html = '<ul>'
        for city in self.cities.all().order_by('name'):
            html += '<li>{}</li>'.format('{}, {}'.format(city.name, city.state.code) if city.state else city.name)
        html += '</ul>'
        return format_html(html)
    get_cities.short_description = 'Cities'

    def get_states_admin(self):
        count = self.states.count()
        if count == 0:
            return None
        elif count == 1:
            return self.states.first()
        html = '<ul>'
        for state in self.states.all().order_by('code'):
            html += '<li>{}</li>'.format(state.code)
        html += '</ul>'
        return format_html(html)
    get_states_admin.short_description = 'States'

    def get_business_types_solicited_admin(self):
        count = self.business_types_solicited.count()
        if count == 0:
            return None
        elif count == 1:
            return self.business_types_solicited.first()
        html = '<ul>'
        for businesstype in self.business_types_solicited.all():
            html += '<li>{}</li>'.format(businesstype.business_type)
        html += '</ul>'
        return format_html(html)
    get_business_types_solicited_admin.short_description = 'Business Types Solicited'

    def get_attachments_admin(self):
        count = self.listingattachment_set.count()
        if count == 0:
            return None
        html = '<ul>'

        if self.website in ['GOVTRIBE.COM', 'SAM.GOV']:
            for listingattachment in self.listingattachment_set.all():
                html += '<li><a href="{}" target="_blank">{}</a></li>'.format(
                    listingattachment.attachment_url, listingattachment.attachment_name)
        else:
            for listingattachment in self.listingattachment_set.all():
                html += '<li><a href="{}" target="_blank">{}</a></li>'.format(
                    listingattachment.attachment.url, os.path.basename(listingattachment.attachment.name))
        html += '</ul>'

        return format_html(html)
    get_attachments_admin.short_description = 'Attachments'

    @property
    def get_states(self):
        return self.states.values_list('code', flat=True)

    @property
    def get_business_types_solicited(self):
        return self.business_types_solicited.values_list('business_type', flat=True)

    @property
    def get_product_service_categories(self):
        return self.product_service_categories.values_list('title', flat=True)

    @property
    def get_shipto_service_locations(self):
        return self.shipto_service_locations.values_list('location_name', flat=True)


class ListingAttachment(models.Model):
    opportunitylisting = models.ForeignKey(OpportunityListing, verbose_name='Opportunity', on_delete=models.CASCADE,
                                           related_name='listingattachments')
    attachment = models.FileField(max_length=500, upload_to='uploads/%Y/%m/%d/', verbose_name='Attachment',
                                  blank=True, null=True)
    attachment_name = models.CharField(max_length=1000, verbose_name='Attachment Name', blank=True, null=True)
    attachment_url = models.CharField(max_length=1000, verbose_name='Attachment URL', blank=True, null=True)

    def __str__(self):
        return self.attachment.name if self.attachment.name else self.attachment_name


class OpportunityContact(models.Model):
    contact = models.ForeignKey(Contact, on_delete=models.DO_NOTHING)
    opportunitylisting = models.ForeignKey(OpportunityListing, on_delete=models.CASCADE)
    contact_website = models.CharField(max_length=100, verbose_name='Website', blank=True, null=True)
    contact_website_id = models.CharField(max_length=200, verbose_name='Contact Website ID', blank=True, null=True)
    position = models.CharField(max_length=200, verbose_name='Position', blank=True, null=True)

    def get_contact_name_admin(self):
        return self.contact.name
    get_contact_name_admin.short_description = 'Name'

    def get_contact_phone_admin(self):
        return self.contact.phone
    get_contact_phone_admin.short_description = 'Phone'

    def get_contact_email_admin(self):
        return self.contact.email
    get_contact_email_admin.short_description = 'Email'


class FavoriteContacts(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user', 'contact')


class FavoriteOpportunities(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    opportunitylisting = models.ForeignKey(OpportunityListing, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user', 'opportunitylisting')


class UserFilter(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    friendly_name = models.CharField(max_length=100, verbose_name='Friendly Name')
    searchterm = models.CharField(max_length=100, verbose_name='Search Term', blank=True, null=True)
    naics_code = models.ForeignKey(
        NAICSCode, verbose_name='NAICS Code', blank=True, null=True, on_delete=models.DO_NOTHING)
    buyer = models.ForeignKey(
        BuyerListing, on_delete=models.DO_NOTHING, blank=True, null=True, verbose_name='Deptt/Agency')
    posting_date_start = models.DateField(verbose_name='Posting Date Start', blank=True, null=True)
    posting_date_end = models.DateField(verbose_name='Posting Date End', blank=True, null=True)
    due_date_start = models.DateField(verbose_name='Due Date Start', blank=True, null=True)
    due_date_end = models.DateField(verbose_name='Due Date End', blank=True, null=True)

    created_date = models.DateTimeField(verbose_name='Created At', auto_now_add=True)
    updated_date = models.DateTimeField(verbose_name='Updated At', auto_now=True)

    class Meta:
        verbose_name = 'User Filter'
        verbose_name_plural = 'User Filters'
        unique_together = ('user', 'friendly_name')


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20, verbose_name='Contact Phone', blank=True, null=True)
    company_name = models.CharField(max_length=200, verbose_name='Company ', blank=True, null=True)

    created_date = models.DateTimeField(verbose_name='Created At', auto_now_add=True)
    updated_date = models.DateTimeField(verbose_name='Updated At', auto_now=True)

    def __str__(self):
        return self.user.username
