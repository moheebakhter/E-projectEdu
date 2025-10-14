from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path("", views.register, name="reg"),
    path("l", views.Login, name="log"),
    path('logout', views.logout_view, name='logout'),



]
