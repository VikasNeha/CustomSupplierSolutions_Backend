from django.urls import path

from . import views


urlpatterns = [
    path('', views.index, name='index'),
    path('api/favoritecontact/', views.mark_contact_favorite, name='mark_contact_favorite'),
    path('api/favoriteopportunity/', views.mark_opportunity_favorite, name='mark_opportunity_favorite'),
    path('api/opportunitystats/', views.get_opportunity_stats, name='get_opportunity_stats'),
]
