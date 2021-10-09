from django.contrib.auth import get_user_model
from djoser.serializers import UserCreateSerializer
from rest_framework import serializers
from rest_framework.authtoken.models import Token

from opportunity.models import BuyerListing, City, Contact, NAICSCode, NIGPCode, OpportunityListing, \
    ProductServiceCategory, ShiptoServiceLocation, State, BusinessType, OpportunityContact, FavoriteContacts, \
    FavoriteOpportunities, ListingAttachment, UserFilter, UserProfile
from opportunity.utilities import get_user_group


User = get_user_model()


class BuyerListingSerializer(serializers.ModelSerializer):
    class Meta:
        model = BuyerListing
        exclude = ['created_date', 'updated_date']


class ProductServiceCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductServiceCategory
        fields = '__all__'


class ShiptoServiceLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShiptoServiceLocation
        fields = '__all__'


class NAICSCodeSerializer(serializers.ModelSerializer):
    formatted = serializers.ReadOnlyField(source='get_formatted')

    class Meta:
        model = NAICSCode
        fields = ['id', 'code', 'title', 'formatted']


class NIGPCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = NIGPCode
        fields = ['code', 'title']


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        exclude = ['id']


class OpportunityContactSerializer(serializers.HyperlinkedModelSerializer):

    contact_id = serializers.ReadOnlyField(source='contact.id')
    contact_name = serializers.ReadOnlyField(source='contact.name')
    contact_email = serializers.ReadOnlyField(source='contact.email')
    contact_phone = serializers.ReadOnlyField(source='contact.phone')
    is_favorite = serializers.SerializerMethodField()

    class Meta:
        model = OpportunityContact
        fields = ['contact_id', 'contact_name', 'contact_email', 'contact_phone', 'position', 'is_favorite']

    def get_is_favorite(self, obj):
        request = self.context.get('request', None)
        if request:
            if FavoriteContacts.objects.filter(user_id=request.user.id, contact_id=obj.contact.id).exists():
                return True
            else:
                return False
        else:
            return False


class StateSerializer(serializers.ModelSerializer):
    class Meta:
        model = State
        fields = ['code', 'name']


class CitySerializer(serializers.ModelSerializer):
    state = serializers.CharField(source='state_repr', read_only=True)

    class Meta:
        model = City
        fields = ['name', 'state']


class BusinessTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessType
        fields = ['business_type']


class ListingAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListingAttachment
        fields = ['id', 'attachment_name', 'attachment_url']


class OpportunityListingSerializer(serializers.ModelSerializer):
    buyer = BuyerListingSerializer(many=False, read_only=True)
    product_service_categories = serializers.ListField(source='get_product_service_categories', read_only=True)
    shipto_service_locations = serializers.ListField(source='get_shipto_service_locations', read_only=True)
    naics_codes = NAICSCodeSerializer(many=True, read_only=True)
    nigp_codes = NIGPCodeSerializer(many=True, read_only=True)
    # contact = ContactSerializer(many=False, read_only=True)
    contacts = OpportunityContactSerializer(source='opportunitycontact_set', many=True)
    cities = CitySerializer(many=True, read_only=True)
    states = serializers.ListField(source='get_states', read_only=True)
    listingattachments = ListingAttachmentSerializer(many=True, read_only=True)
    is_favorite = serializers.SerializerMethodField()
    posting_summary = serializers.SerializerMethodField()

    class Meta:
        model = OpportunityListing
        fields = [
            'id', 'website', 'posting_id', 'title', 'posting_date', 'bidding_open_date', 'submission_deadline',
            'opportunity_amount', 'contract_length', 'posting_type', 'posting_url', 'posting_summary',
            'pre_submission_meeting', 'buyer', 'product_service_categories', 'shipto_service_locations', 'naics_codes',
            'nigp_codes', 'cities', 'states', 'business_types_solicited', 'created_date', 'updated_date', 'contacts',
            'listingattachments', 'is_favorite', 'is_deadline_ongoing']

    def get_is_favorite(self, obj):
        request = self.context.get('request', None)
        if request:
            if FavoriteOpportunities.objects.filter(user_id=request.user.id, opportunitylisting=obj.id).exists():
                return True
            else:
                return False
        else:
            return False

    def get_posting_summary(self, obj: OpportunityListing):
        if isinstance(self.instance, OpportunityListing):
            return obj.posting_summary
        else:
            posting_summary = obj.posting_summary[:500]
            if len(obj.posting_summary) > 500:
                posting_summary = f'{posting_summary}...'
            return posting_summary


class FavoriteContactsSerializer(serializers.ModelSerializer):
    contact_id = serializers.ReadOnlyField(source='contact.id')
    contact_name = serializers.ReadOnlyField(source='contact.name')
    contact_email = serializers.ReadOnlyField(source='contact.email')
    contact_phone = serializers.ReadOnlyField(source='contact.phone')

    class Meta:
        model = FavoriteContacts
        fields = ['contact_id', 'contact_name', 'contact_email', 'contact_phone']


class UserSerializer(serializers.ModelSerializer):
    group = serializers.SerializerMethodField()
    company_name = serializers.ReadOnlyField(source='userprofile.company_name')
    phone = serializers.ReadOnlyField(source='userprofile.phone')

    class Meta:
        fields = ('id', 'first_name', 'last_name', 'username', 'group', 'email', 'company_name', 'phone')
        model = User

    def get_group(self, obj: User):
        request = self.context.get('request', None)
        if request:
            return get_user_group(obj)
        else:
            return 'BASIC'


class TokenSerializer(serializers.ModelSerializer):
    auth_token = serializers.CharField(source="key")
    group = serializers.SerializerMethodField()
    id = serializers.ReadOnlyField(source='user.id')
    first_name = serializers.ReadOnlyField(source='user.first_name')
    last_name = serializers.ReadOnlyField(source='user.last_name')
    username = serializers.ReadOnlyField(source='user.username')
    email = serializers.ReadOnlyField(source='user.email')
    company_name = serializers.ReadOnlyField(source='user.userprofile.company_name')
    phone = serializers.ReadOnlyField(source='user.userprofile.phone')

    class Meta:
        model = Token
        fields = ("id", "auth_token", "group", "first_name", "last_name", "username", "email", "company_name", "phone")

    def get_group(self, obj):
        return get_user_group(obj.user)


class CustomUserCreateSerializer(UserCreateSerializer):
    def validate(self, attrs):
        if User.objects.filter(email=attrs['email']).exists():
            raise serializers.ValidationError(
                {"non_field_errors": "A User with this Email already exists"}
            )

        attrs['username'] = attrs['email']
        return super().validate(attrs)


class UserFilterSerializer(serializers.ModelSerializer):
    naics_code_data = NAICSCodeSerializer(many=False, read_only=True, source='naics_code')
    buyer_data = BuyerListingSerializer(many=False, read_only=True, source='buyer')
    opportunities_count = serializers.SerializerMethodField()

    class Meta:
        model = UserFilter
        fields = ('id', 'friendly_name', 'searchterm', 'posting_date_start', 'posting_date_end', 'due_date_start',
                  'due_date_end', 'naics_code_data', 'buyer_data', 'naics_code', 'buyer', 'opportunities_count')
        extra_kwargs = {
            'naics_code': {'write_only': True},
            'buyer': {'write_only': True}
        }

    def create(self, validated_data):
        return UserFilter.objects.create(**validated_data)

    def update(self, instance: UserFilter, validated_data):
        instance.friendly_name = validated_data['friendly_name']
        instance.searchterm = validated_data['searchterm']
        instance.naics_code = validated_data['naics_code']
        instance.buyer = validated_data['buyer']
        instance.posting_date_start = validated_data['posting_date_start']
        instance.posting_date_end = validated_data['posting_date_end']
        instance.due_date_start = validated_data['due_date_start']
        instance.due_date_end = validated_data['due_date_end']
        instance.save()
        return instance

    def validate(self, data):
        request = self.context.get('request', None)
        user_group = get_user_group(request.user)

        if user_group == 'BASIC' and request.method in ['PUT', 'DELETE']:
            raise serializers.ValidationError("Please Upgrade Your Plan!")

        if request.method == 'PUT' and self.instance is None:
            raise serializers.ValidationError("No Such Filter Exists!")

        if request.method == 'POST':
            if user_group == 'BASIC' and UserFilter.objects.filter(user_id=request.user.id).exists():
                raise serializers.ValidationError('You have exceeded maximum number of saved filters!')
            if UserFilter.objects.filter(user_id=request.user.id, friendly_name=data['friendly_name']).exists():
                raise serializers.ValidationError('Filter with this name already exists!')

        if request.method == 'PUT':
            if UserFilter.objects.filter(
                    user_id=request.user.id, friendly_name=data['friendly_name']).exclude(id=self.instance.id).exists():
                raise serializers.ValidationError('Filter with this name already exists!')

        if data.get('searchterm', '').strip() == '' and \
                data.get('naics_code') is None and \
                data.get('buyer') is None and \
                data.get('posting_date_start', '').strip() == '' and \
                data.get('posting_date_end', '').strip() == '' and \
                data.get('due_date_start', '').strip() == '' and \
                data.get('due_date_end', '').strip() == '':
            raise serializers.ValidationError('At least one field is mandatory!')

        queryset = UserFilter.objects.filter(user_id=request.user.id)
        if 'searchterm' in data and data['searchterm'] and data.get('searchterm', '').strip() != '':
            queryset = queryset.filter(searchterm=data['searchterm'])
        if 'naics_code' in data and data['naics_code'] is not None:
            queryset = queryset.filter(naics_code=data['naics_code'])
        if 'buyer' in data and data['buyer'] is not None:
            queryset = queryset.filter(buyer=data['buyer'])
        if 'posting_date_start' in data and data['posting_date_start'] and data.get('posting_date_start', '') != '':
            queryset = queryset.filter(posting_date_start=data['posting_date_start'])
        if 'posting_date_end' in data and data['posting_date_end'] and data.get('posting_date_end', '') != '':
            queryset = queryset.filter(posting_date_end=data['posting_date_end'])
        if 'due_date_start' in data and data['due_date_start'] and data.get('due_date_start', '') != '':
            queryset = queryset.filter(due_date_start=data['due_date_start'])
        if 'due_date_end' in data and data['due_date_end'] and data.get('due_date_end', '') != '':
            queryset = queryset.filter(due_date_end=data['due_date_end'])
        if queryset.exists():
            raise serializers.ValidationError('A Filter with provided filter values already exists!')

        data['user_id'] = request.user.id
        return data

    def get_opportunities_count(self, obj: UserFilter):
        queryset = OpportunityListing.objects.all()

        if obj.naics_code:
            queryset = queryset.filter(naics_codes__id=obj.naics_code_id)
        if obj.buyer:
            queryset = queryset.filter(buyer_id=obj.buyer_id)
        if obj.posting_date_start:
            queryset = queryset.filter(posting_date__date__gte=obj.posting_date_start)
        if obj.posting_date_end:
            queryset = queryset.filter(posting_date__date__lte=obj.posting_date_end)
        if obj.due_date_start:
            queryset = queryset.filter(submission_deadline__date__gte=obj.due_date_start)
        if obj.due_date_end:
            queryset = queryset.filter(submission_deadline__date__lte=obj.due_date_end)
        if obj.searchterm and obj.searchterm.strip() != '':
            queryset = queryset.filter(search_vector=obj.searchterm)
        return queryset.count()


class UserProfileSerializer(serializers.ModelSerializer):
    first_name = serializers.ReadOnlyField(source='user.first_name')
    last_name = serializers.ReadOnlyField(source='user.last_name')
    email = serializers.ReadOnlyField(source='user.email')

    class Meta:
        model = UserProfile
        fields = ('first_name', 'last_name', 'email', 'phone', 'company_name')

    def update(self, instance: UserProfile, validated_data):
        if 'first_name' in validated_data:
            instance.user.first_name = validated_data['first_name'].strip()
        if 'last_name' in validated_data:
            instance.user.last_name = validated_data['last_name'].strip()
        if 'email' in validated_data:
            instance.user.email = validated_data['email'].strip()
        if 'company_name' in validated_data:
            instance.company_name = validated_data['company_name'].strip()
        if 'phone' in validated_data:
            instance.phone = validated_data['phone'].strip()
        instance.save()
        instance.user.save()
        return instance

    def validate(self, data):
        request = self.context.get('request', None)
        if request.method == 'PUT':
            if 'email' in request.data:
                if request.data['email'].strip() == '':
                    raise serializers.ValidationError('Email is Required')

                if User.objects.exclude(id=request.user.id).filter(email=request.data['email']).exists():
                    raise serializers.ValidationError('This Email already exists for another user')
        data.update(request.data)
        return data
