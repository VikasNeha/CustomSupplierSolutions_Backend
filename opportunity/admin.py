from django.contrib import admin

from opportunity.models import *


admin.site.site_header = 'Opportunity URLs'
admin.site.site_title = 'Opportunity URLs'
admin.site.index_title = 'Opportunity URLs'


@admin.register(BuyerListing)
class BuyerListingAdmin(admin.ModelAdmin):
    list_display = ['buyer_name', 'website', 'buyer_url']
    readonly_fields = ['buyer_name', 'website', 'buyer_url']
    search_fields = ['buyer_name']
    list_filter = ['website']


class OpportunityContactInline(admin.TabularInline):
    model = OpportunityContact

    readonly_fields = ['get_contact_name_admin', 'get_contact_email_admin', 'get_contact_phone_admin', 'position']
    exclude = ['contact', 'contact_website', 'contact_website_id', 'id']

    def get_extra(self, request, obj=None, **kwargs):
        return 0

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(OpportunityListing)
class OpportunityListingAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'website', 'buyer', 'get_posting_date', 'get_bidding_open_date', 'submission_deadline',
        'opportunity_amount', 'posting_type'
    ]
    list_filter = [
        'website', 'posting_date', 'bidding_open_date', 'submission_deadline', 'posting_type',
        'product_service_categories', 'shipto_service_locations', 'naics_codes', 'cities', 'states', 'opportunity_type',
        'buyer'
    ]
    suit_list_filter_horizontal = [
        'product_service_categories', 'shipto_service_locations', 'naics_codes', 'cities', 'states', 'buyer'
    ]
    readonly_fields = [
        'title', 'website', 'posting_id', 'get_posting_url', 'get_naics_codes', 'get_cities', 'get_states_admin',
        'location', 'get_nigp_codes', 'buyer', 'posting_date', 'bidding_open_date', 'submission_deadline',
        'pre_submission_meeting', 'opportunity_amount', 'posting_type', 'contract_length',
        'get_product_service_categories_admin', 'get_shipto_service_locations_admin', 'get_contact',
        'get_posting_summary', 'get_business_types_solicited_admin', 'get_attachments_admin', 'opportunity_type',
        'set_aside_type', 'solicitation_number', 'contract_start_date'
    ]
    exclude = [
        'posting_summary', 'posting_url', 'product_service_categories', 'shipto_service_locations', 'naics_codes',
        'contact', 'nigp_codes', 'cities', 'states', 'business_types_solicited'
    ]
    search_fields = ['title', 'posting_summary', 'buyer__buyer_name']
    ordering = ['-posting_date']
    # inlines = [OpportunityContactInline]


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'company_name']
