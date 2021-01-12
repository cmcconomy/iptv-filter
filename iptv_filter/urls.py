from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('m3u', views.m3u_api, name='m3u_api'),
    path('epg', views.epg_api, name='epg_api'),
    path('configure', views.configure, name='configure'),
    path('channels', views.channel_api, name='channel_api'),
    path('channels/<int:id>', views.channel_api, name='channel_api_with_id'),
    path('retrieve/m3u', views._retrieve_m3u, name='retm3u'),
    path('retrieve/epg', views._retrieve_epg, name='retepg'),
    path('update/m3u', views._update_m3u_tables, name='updm3u'),
    path('update/epg', views._update_epg_tables, name='updepg'),
]