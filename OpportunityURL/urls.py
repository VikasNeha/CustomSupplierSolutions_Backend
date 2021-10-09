"""OpportunityURL URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import routers

from opportunity.views import OpportunityListingViewSet, NAICSCodeViewSet, BuyerViewSet, FavoriteContactsViewSet, \
    UserFilterViewSet, UserProfileViewSet

router = routers.DefaultRouter()
router.register(r'opportunitylistings', OpportunityListingViewSet)
router.register(r'naicscodes', NAICSCodeViewSet)
router.register(r'departments', BuyerViewSet)
router.register(r'favoritecontacts', FavoriteContactsViewSet)
router.register(r'myfilters', UserFilterViewSet)
router.register(r'userprofile', UserProfileViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('opportunity.urls')),
    path('api/', include(router.urls)),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('auth/', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
