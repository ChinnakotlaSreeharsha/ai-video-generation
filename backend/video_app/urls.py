from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path("translate/", views.translate_api, name="translate"),
    path('generate-audio/', views.generate_audio, name='generate_audio'),
    path("upload-avatar/", views.upload_avatar, name="upload_avatar"),
    path("process-avatar/", views.process_avatar, name="process_avatar"),
]