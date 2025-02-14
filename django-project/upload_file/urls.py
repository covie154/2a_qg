from django.contrib import admin  
from django.urls import path  
from upload_file import views  
urlpatterns = [  
    path('index/', views.index),  
]  