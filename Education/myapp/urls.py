from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path("", views.register, name="reg"),
    path("l", views.Login, name="log"),
    path("i", views.Index, name="index"),
    path("a", views.About, name="about"),
    path("c", views.Course, name="course"),
    path("con", views.Contact, name="con"),
    path('logout', views.logout_view, name='logout'),



]
