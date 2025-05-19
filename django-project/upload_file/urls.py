from django.contrib import admin  
from django.urls import path  
from upload_file import views
from upload_file.views import toggle_chosen  

urlpatterns = [  
    path('', views.index, name='index'),
    path('result/<str:task_id>/', views.result_view, name='result_view'),
    path('all-questions/', views.list_questions, name='list_questions'),
    path('questions/', views.selected_questions, name='selected_questions'),
    path('all-tasks/', views.tasks_all, name='tasks_all'),
    path('task/<str:task_id>/', views.task_view, name='task_view'),
    path('q/<int:qn_id>/', views.qn_view, name='question_detail'),
    path('toggle-chosen/<int:qn_id>/', toggle_chosen, name='toggle_chosen'),
]