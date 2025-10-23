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
    path('new', views.blog_list, name='blog_list'),
    path('predict/', views.predict_view, name='predict'),
    path("dropout/", views.dropout_view, name="dropout"),
    path('logout', views.logout_view, name='logout'),
    path('admin', views.home, name='home'),
    path('students/', views.students_list, name='students_list'),
    path('students/add/', views.students_add, name='students_add'),
    path('students/edit/<str:doc_id>/', views.students_edit, name='students_edit'),
    path('courses/', views.courses_list, name='courses_list'),
    path('courses/add/', views.courses_add, name='courses_add'),
    path('courses/edit/<str:doc_id>/', views.courses_edit, name='courses_edit'),



]
