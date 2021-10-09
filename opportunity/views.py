from datetime import datetime, timedelta

from django.contrib.postgres.search import SearchQuery
from django.db.models import Q
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import viewsets, filters
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from opportunity.models import OpportunityListing, NAICSCode, BuyerListing, FavoriteContacts, FavoriteOpportunities, \
    UserFilter, UserProfile
from opportunity.serializers import OpportunityListingSerializer, NAICSCodeSerializer, BuyerListingSerializer, \
    FavoriteContactsSerializer, UserFilterSerializer, UserProfileSerializer


def index(request):
    return render(request, 'opportunity/index.html')


class OpportunityListingViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = OpportunityListing.objects.all()
    serializer_class = OpportunityListingSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_date']
    ordering = ['-created_date']

    def get_queryset(self):
        queryset = OpportunityListing.objects.all()

        showgrants = self.request.query_params.get('showgrants', None)
        if showgrants is not None and showgrants == '1':
            queryset = queryset.filter(posting_type='GRANT')
        else:
            if self.action != 'retrieve':
                queryset = queryset.exclude(posting_type='GRANT')

        naicscode = self.request.query_params.get('naicscode', None)
        if naicscode is not None:
            queryset = queryset.filter(naics_codes__code=naicscode)

        buyer_id = self.request.query_params.get('department', None)
        if buyer_id is not None:
            queryset = queryset.filter(buyer_id=buyer_id)

        contact_id = self.request.query_params.get('contactid', None)
        if contact_id is not None:
            queryset = queryset.filter(opportunitycontact__contact_id=contact_id)

        favorite = self.request.query_params.get('favorite', None)
        if favorite is not None and favorite == '1':
            queryset = queryset.filter(favoriteopportunities__user=self.request.user)

        posting_date_start = self.request.query_params.get('posting_date_start', None)
        if posting_date_start is not None:
            queryset = queryset.filter(posting_date__date__gte=datetime.strptime(posting_date_start, '%Y-%m-%d').date())

        posting_date_end = self.request.query_params.get('posting_date_end', None)
        if posting_date_end is not None:
            queryset = queryset.filter(posting_date__date__lte=datetime.strptime(posting_date_end, '%Y-%m-%d').date())

        due_date_start = self.request.query_params.get('due_date_start', None)
        if due_date_start is not None:
            due_date_start = datetime.strptime(due_date_start, '%Y-%m-%d').date()
            queryset = queryset.filter(Q(submission_deadline__date__gte=due_date_start) | Q(is_deadline_ongoing=True))

        due_date_end = self.request.query_params.get('due_date_end', None)
        if due_date_end is not None:
            due_date_end = datetime.strptime(due_date_end, '%Y-%m-%d').date()
            queryset = queryset.filter(Q(submission_deadline__date__lte=due_date_end) | Q(is_deadline_ongoing=True))

        searchterm = self.request.query_params.get('searchterm', '').strip()
        if searchterm != '':
            queryset = queryset.filter(search_vector=SearchQuery(searchterm, search_type='phrase'))

        state_code = self.request.query_params.get('state', None)
        if state_code is not None:
            queryset = queryset.filter(states__code=state_code)

        return queryset


class NAICSCodeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = NAICSCode.objects.all()
    serializer_class = NAICSCodeSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = NAICSCode.objects.all()

        code = self.request.query_params.get('code', None)
        if code is not None:
            queryset = queryset.filter(code=code)

        searchterm = self.request.query_params.get('searchterm', None)
        if searchterm is not None:
            queryset = queryset.filter(Q(code__icontains=searchterm) | Q(title__icontains=searchterm))

        return queryset


class BuyerViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = BuyerListing.objects.all()
    serializer_class = BuyerListingSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = BuyerListing.objects.all()

        deptt_id = self.request.query_params.get('id', None)
        if deptt_id is not None:
            queryset = queryset.filter(pk=deptt_id)

        searchterm = self.request.query_params.get('searchterm', None)
        if searchterm is not None:
            queryset = queryset.filter(buyer_name__icontains=searchterm)

        return queryset


class FavoriteContactsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FavoriteContacts.objects.all()
    serializer_class = FavoriteContactsSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return FavoriteContacts.objects.filter(user=self.request.user)


class UserFilterViewSet(viewsets.ModelViewSet):
    queryset = UserFilter.objects.all()
    serializer_class = UserFilterSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super(UserFilterViewSet, self).dispatch(*args, **kwargs)

    def get_queryset(self):
        return UserFilter.objects.filter(user=self.request.user)


class UserProfileViewSet(viewsets.ModelViewSet):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super(UserProfileViewSet, self).dispatch(*args, **kwargs)

    def get_queryset(self):
        # if self.action == 'retrieve':
        self.kwargs['pk'] = UserProfile.objects.get(user=self.request.user).id
        return UserProfile.objects.filter(user=self.request.user)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mark_contact_favorite(request):
    set_favorite = request.query_params.get('set', '0')

    if set_favorite == '1':
        try:
            FavoriteContacts.objects.get_or_create(
                contact_id=request.query_params['contact_id'], user_id=request.user.id)
            return Response({'success': True})
        except:
            return Response({'success': False})
    else:
        try:
            FavoriteContacts.objects.filter(
                contact_id=request.query_params['contact_id'], user_id=request.user.id).delete()
            return Response({'success': True})
        except:
            return Response({'success': False})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mark_opportunity_favorite(request):
    set_favorite = request.query_params.get('set', '0')

    if set_favorite == '1':
        try:
            FavoriteOpportunities.objects.get_or_create(
                opportunitylisting_id=request.query_params['opportunitylisting_id'], user_id=request.user.id)
            return Response({'success': True})
        except:
            return Response({'success': False})
    else:
        try:
            FavoriteOpportunities.objects.filter(
                opportunitylisting_id=request.query_params['opportunitylisting_id'], user_id=request.user.id).delete()
            return Response({'success': True})
        except:
            return Response({'success': False})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_opportunity_stats(request):
    datetime_before_24_hrs = datetime.now() - timedelta(hours=24)
    return Response({
        'count_last_24_hrs': OpportunityListing.objects.filter(created_date__gte=datetime_before_24_hrs).count()
    })
