from django.contrib import admin
from django.urls import path, include
from upload_file import views as upload_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('upload/', include('upload_file.urls')),
    path('q/<int:qn_id>/', upload_views.qn_view, name='question_detail'),
    path('questions/', views.list_questions, name='list_questions'),
    path('celery-progress/', include('celery_progress.urls')),
]
