from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('m3u', views.m3u_api, name='m3u_api'),
]