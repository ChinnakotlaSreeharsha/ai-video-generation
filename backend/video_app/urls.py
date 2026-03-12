from django.urls import path
from . import views

urlpatterns = [
    # ── Public ────────────────────────────────────────────────
    path('',               views.index,              name='home'),

    # ── Auth ──────────────────────────────────────────────────
    path('login/',         views.login_view,          name='login'),
    path('logout/',        views.logout_view,         name='logout'),
    path('register/',      views.register_view,       name='register'),

    # ── Dashboard ─────────────────────────────────────────────
    path('dashboard/',     views.dashboard,           name='dashboard'),

    # ── Profile & Settings ────────────────────────────────────
    path('profile/',         views.profile_settings,  name='profile_settings'),
    path('profile/update/',  views.update_profile,    name='update_profile'),
    path('profile/delete/',  views.delete_account,    name='delete_account'),

    # ── Avatar Library (platform + user) ──────────────────────
    path('avatars/',                  views.avatar_library,     name='avatar_library'),
    path('avatars/upload/',           views.user_avatar_upload, name='user_avatar_upload'),
    path('avatars/delete/<int:pk>/',  views.user_avatar_delete, name='user_avatar_delete'),

    # ── My Videos ─────────────────────────────────────────────
    path('my-videos/',       views.my_videos,          name='my_videos'),

    # ── Pipeline ──────────────────────────────────────────────
    path('generate-audio/',  views.generate_audio,    name='generate_audio'),
    path('upload-avatar/',   views.upload_avatar,     name='upload_avatar'),   # legacy redirect
    path('process-avatar/',  views.process_avatar,    name='process_avatar'),

    # ── Translation API ───────────────────────────────────────
    path('translate/',       views.translate_api,     name='translate'),
]