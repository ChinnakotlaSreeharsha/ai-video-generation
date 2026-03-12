import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(BASE_DIR)

import time
import logging

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.conf import settings
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from ml_pipeline.ml1_tts.process_tts import generate_tts
from ml_pipeline.ml1_tts.translator import translate_text
from ml_pipeline.run_pipeline import run_pipeline


# ─────────────────────────────────────────────
# Logger
# ─────────────────────────────────────────────

logger = logging.getLogger("video_app")


def _log_step(step_name: str, start: float, extra: str = "") -> None:
    elapsed = time.perf_counter() - start
    suffix  = f" | {extra}" if extra else ""
    logger.info("[%s] completed in %.3fs%s", step_name, elapsed, suffix)


# ─────────────────────────────────────────────
# Public pages
# ─────────────────────────────────────────────

def index(request):
    return render(request, "video_app/index.html")


def page_not_found(request, exception=None):
    return render(request, "video_app/404.html", status=404)


# ─────────────────────────────────────────────
# Authentication — Register
# ─────────────────────────────────────────────

def register_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        t0 = time.perf_counter()

        username   = request.POST.get("username", "").strip()
        email      = request.POST.get("email", "").strip()
        first_name = request.POST.get("first_name", "").strip()
        last_name  = request.POST.get("last_name", "").strip()
        password1  = request.POST.get("password1", "")
        password2  = request.POST.get("password2", "")

        logger.info("[register] attempt | username=%s email=%s", username, email)

        if not username or not email or not password1:
            messages.error(request, "Username, email and password are required.")
            return render(request, "video_app/register.html")

        if password1 != password2:
            messages.error(request, "Passwords do not match.")
            return render(request, "video_app/register.html")

        if len(password1) < 8:
            messages.error(request, "Password must be at least 8 characters.")
            return render(request, "video_app/register.html")

        if User.objects.filter(username=username).exists():
            messages.error(request, "That username is already taken.")
            return render(request, "video_app/register.html")

        if User.objects.filter(email=email).exists():
            messages.error(request, "An account with that email already exists.")
            return render(request, "video_app/register.html")

        try:
            t_user = time.perf_counter()
            user = User.objects.create_user(
                username=username, email=email, password=password1,
                first_name=first_name, last_name=last_name,
            )
            _log_step("register:create_user", t_user, f"user_id={user.id}")
        except Exception as exc:
            logger.error("[register] user creation failed | %s", exc, exc_info=True)
            messages.error(request, "An unexpected error occurred. Please try again.")
            return render(request, "video_app/register.html")

        if request.FILES.get("avatar"):
            try:
                t_avatar    = time.perf_counter()
                avatar_file = request.FILES["avatar"]
                avatar_dir  = os.path.join(settings.MEDIA_ROOT, "profile_avatars")
                os.makedirs(avatar_dir, exist_ok=True)
                avatar_path = os.path.join(avatar_dir, f"user_{user.id}_{avatar_file.name}")
                with open(avatar_path, "wb+") as f:
                    for chunk in avatar_file.chunks():
                        f.write(chunk)
                user.profile.avatar = f"profile_avatars/user_{user.id}_{avatar_file.name}"
                user.profile.save()
                _log_step("register:save_avatar", t_avatar, f"file={avatar_file.name}")
            except Exception as exc:
                logger.warning("[register] avatar upload failed | user_id=%s | %s",
                               user.id, exc, exc_info=True)
                messages.warning(request, "Profile photo could not be saved, but your account was created.")

        login(request, user)
        _log_step("register:total", t0, f"user={username}")
        messages.success(request, f"Welcome to Stackly, {user.first_name or user.username}!")
        return redirect("dashboard")

    return render(request, "video_app/register.html")


# ─────────────────────────────────────────────
# Authentication — Login
# ─────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        t0       = time.perf_counter()
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        logger.info("[login] attempt | username=%s", username)

        try:
            user = authenticate(request, username=username, password=password)
        except Exception as exc:
            logger.error("[login] authentication error | %s", exc, exc_info=True)
            messages.error(request, "An error occurred during sign-in. Please try again.")
            return render(request, "video_app/login.html")

        if user is not None:
            login(request, user)
            _log_step("login:authenticate", t0, f"user={username}")
            next_url = request.GET.get("next", "dashboard")
            return redirect(next_url)
        else:
            logger.warning("[login] failed | username=%s", username)
            messages.error(request, "Invalid username or password.")

    return render(request, "video_app/login.html")


# ─────────────────────────────────────────────
# Authentication — Logout
# ─────────────────────────────────────────────

@login_required
def logout_view(request):
    logger.info("[logout] user=%s", request.user.username)
    logout(request)
    return redirect("home")


# ─────────────────────────────────────────────
# Profile & Settings
# ─────────────────────────────────────────────

@login_required
def profile_settings(request):
    from .models import UserProfile, VideoGeneration
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    video_count = VideoGeneration.objects.filter(user=request.user, status="done").count()
    return render(request, "video_app/profile_settings.html", {
        "profile":     profile,
        "video_count": video_count,
    })


@login_required
def update_profile(request):
    if request.method != "POST":
        return redirect("profile_settings")

    from .models import UserProfile
    t0         = time.perf_counter()
    user       = request.user
    profile, _ = UserProfile.objects.get_or_create(user=user)
    form_type  = request.POST.get("form_type", "profile")

    logger.info("[update_profile] form_type=%s | user=%s", form_type, user.username)

    if form_type == "profile":
        try:
            user.first_name = request.POST.get("first_name", user.first_name).strip()
            user.last_name  = request.POST.get("last_name",  user.last_name).strip()
            user.email      = request.POST.get("email",      user.email).strip()

            new_username = request.POST.get("username", user.username).strip()
            if new_username != user.username and User.objects.filter(username=new_username).exists():
                messages.error(request, "That username is already taken.")
                return redirect("profile_settings")
            user.username = new_username

            profile.bio = request.POST.get("bio", profile.bio or "").strip()

            if request.FILES.get("avatar"):
                t_avatar    = time.perf_counter()
                avatar_file = request.FILES["avatar"]
                avatar_dir  = os.path.join(settings.MEDIA_ROOT, "profile_avatars")
                os.makedirs(avatar_dir, exist_ok=True)
                ext       = avatar_file.name.rsplit(".", 1)[-1]
                filename  = f"user_{user.id}.{ext}"
                full_path = os.path.join(avatar_dir, filename)
                with open(full_path, "wb+") as f:
                    for chunk in avatar_file.chunks():
                        f.write(chunk)
                profile.avatar = f"profile_avatars/{filename}"
                _log_step("update_profile:save_avatar", t_avatar, f"file={filename}")

            user.save()
            profile.save()
            _log_step("update_profile:profile", t0, f"user={user.username}")
            messages.success(request, "Profile updated successfully.")

        except Exception as exc:
            logger.error("[update_profile] failed | user=%s | %s", user.username, exc, exc_info=True)
            messages.error(request, "An unexpected error occurred. Please try again.")

    elif form_type == "password":
        old_pw  = request.POST.get("old_password", "")
        new_pw1 = request.POST.get("new_password1", "")
        new_pw2 = request.POST.get("new_password2", "")

        if not user.check_password(old_pw):
            logger.warning("[update_profile] incorrect current password | user=%s", user.username)
            messages.error(request, "Current password is incorrect.")
            return redirect("profile_settings#security")

        if new_pw1 != new_pw2:
            messages.error(request, "New passwords do not match.")
            return redirect("profile_settings#security")

        if len(new_pw1) < 8:
            messages.error(request, "New password must be at least 8 characters.")
            return redirect("profile_settings#security")

        try:
            user.set_password(new_pw1)
            user.save()
            update_session_auth_hash(request, user)
            _log_step("update_profile:password", t0, f"user={user.username}")
            messages.success(request, "Password changed successfully.")
        except Exception as exc:
            logger.error("[update_profile] password change failed | user=%s | %s",
                         user.username, exc, exc_info=True)
            messages.error(request, "An unexpected error occurred. Please try again.")

    else:
        try:
            profile.save()
            _log_step("update_profile:preferences", t0, f"user={user.username}")
            messages.success(request, "Preferences saved.")
        except Exception as exc:
            logger.error("[update_profile] preferences failed | user=%s | %s",
                         user.username, exc, exc_info=True)
            messages.error(request, "An unexpected error occurred. Please try again.")

    return redirect("profile_settings")


@login_required
def delete_account(request):
    username = request.user.username
    logger.info("[delete_account] initiated | user=%s", username)
    try:
        user = request.user
        logout(request)
        user.delete()
        logger.info("[delete_account] completed | user=%s", username)
        messages.success(request, "Your account has been permanently deleted.")
    except Exception as exc:
        logger.error("[delete_account] failed | user=%s | %s", username, exc, exc_info=True)
        messages.error(request, "An unexpected error occurred. Please contact support.")
    return redirect("home")


# ─────────────────────────────────────────────
# Dashboard
# ─────────────────────────────────────────────

@login_required
def dashboard(request):
    from .models import VideoGeneration, Avatar, UserAvatar

    videos       = VideoGeneration.objects.filter(user=request.user, status="done").select_related("avatar")
    latest_video = videos.first()

    # Merge platform avatars + user's own usable avatars for the mini-picker
    platform_avatars = list(Avatar.objects.filter(is_active=True))
    user_avatars_qs  = UserAvatar.objects.filter(owner=request.user, is_active=True)
    user_avatars     = [ua for ua in user_avatars_qs if ua.is_usable]

    return render(request, "video_app/dashboard.html", {
        "videos":          videos[:5],
        "latest_video":    latest_video,
        "avatars":         platform_avatars,
        "user_avatars":    user_avatars,
    })


# ─────────────────────────────────────────────
# Avatar Library
# ─────────────────────────────────────────────

@login_required
def avatar_library(request):
    """
    Full avatar selection grid.
    Shows platform avatars + the logged-in user's own usable UserAvatars.
    Both lists respect the ?category= filter.
    """
    from .models import Avatar, UserAvatar

    category   = request.GET.get("category", "")
    categories = Avatar.CATEGORY_CHOICES

    # Platform avatars
    platform_qs = Avatar.objects.filter(is_active=True)
    if category:
        platform_qs = platform_qs.filter(category=category)

    # User's own avatars: private (always usable) + approved public
    user_qs = (
        UserAvatar.objects.filter(owner=request.user, is_active=True, is_public=False)
        | UserAvatar.objects.filter(
            owner=request.user, is_active=True,
            is_public=True, review_status="approved",
        )
    )
    if category:
        user_qs = user_qs.filter(category=category)

    return render(request, "video_app/avatar_library.html", {
        "avatars":         platform_qs,
        "user_avatars":    user_qs,
        "categories":      categories,
        "active_category": category,
    })


# ─────────────────────────────────────────────
# User Avatar — Upload
# ─────────────────────────────────────────────

@login_required
def user_avatar_upload(request):
    """
    Shows the upload form and the user's existing avatar uploads.
    POST: validates, saves, sets review_status automatically.
    """
    from .models import UserAvatar

    user_avatars = UserAvatar.objects.filter(owner=request.user, is_active=True)

    if request.method == "POST":
        t0 = time.perf_counter()

        name        = request.POST.get("name", "").strip()
        category    = request.POST.get("category", "custom").strip()
        description = request.POST.get("description", "").strip()
        is_public   = request.POST.get("is_public", "false") == "true"

        if not name:
            messages.error(request, "Please give your avatar a name.")
            return render(request, "video_app/user_avatar_upload.html",
                          {"user_avatars": user_avatars})

        source_video_file = request.FILES.get("source_video")
        if not source_video_file:
            messages.error(request, "A source video is required.")
            return render(request, "video_app/user_avatar_upload.html",
                          {"user_avatars": user_avatars})

        MAX_VIDEO_MB = 200
        MAX_IMG_MB   = 5

        if source_video_file.size > MAX_VIDEO_MB * 1024 * 1024:
            messages.error(request, f"Source video exceeds the {MAX_VIDEO_MB} MB limit.")
            return render(request, "video_app/user_avatar_upload.html",
                          {"user_avatars": user_avatars})

        preview_file = request.FILES.get("preview_image")
        if preview_file and preview_file.size > MAX_IMG_MB * 1024 * 1024:
            messages.error(request, f"Thumbnail image exceeds the {MAX_IMG_MB} MB limit.")
            return render(request, "video_app/user_avatar_upload.html",
                          {"user_avatars": user_avatars})

        try:
            ua = UserAvatar(
                owner        = request.user,
                name         = name,
                category     = category,
                description  = description,
                is_public    = is_public,
                source_video = source_video_file,
                # Private avatars are auto-approved; public ones need review
                review_status = "approved" if not is_public else "pending",
            )
            if preview_file:
                ua.preview_image = preview_file
            ua.save()

            _log_step("user_avatar_upload", t0,
                      f"user={request.user.username} name={name} public={is_public}")

            if is_public:
                messages.success(request,
                    f"'{name}' uploaded! It will appear in the public library after review.")
            else:
                messages.success(request,
                    f"'{name}' is ready to use in your avatar library!")

        except Exception as exc:
            logger.error("[user_avatar_upload] failed | user=%s | %s",
                         request.user.username, exc, exc_info=True)
            messages.error(request, "An error occurred while saving your avatar. Please try again.")

        return redirect("user_avatar_upload")

    return render(request, "video_app/user_avatar_upload.html",
                  {"user_avatars": user_avatars})


# ─────────────────────────────────────────────
# User Avatar — Delete (soft)
# ─────────────────────────────────────────────

@login_required
def user_avatar_delete(request, pk):
    """Soft-delete a user's own avatar (sets is_active=False)."""
    from .models import UserAvatar

    if request.method != "POST":
        return redirect("user_avatar_upload")

    try:
        ua = UserAvatar.objects.get(pk=pk, owner=request.user)
        ua.is_active = False
        ua.save()
        messages.success(request, f"'{ua.name}' has been removed from your library.")
        logger.info("[user_avatar_delete] pk=%s user=%s", pk, request.user.username)
    except UserAvatar.DoesNotExist:
        messages.error(request, "Avatar not found.")

    return redirect("user_avatar_upload")


# ─────────────────────────────────────────────
# My Generated Videos
# ─────────────────────────────────────────────

@login_required
def my_videos(request):
    from .models import VideoGeneration
    videos = VideoGeneration.objects.filter(user=request.user).select_related("avatar")
    return render(request, "video_app/my_videos.html", {"videos": videos})


# ─────────────────────────────────────────────
# HELPER: absolute path → browser URL
# ─────────────────────────────────────────────

def path_to_url(abs_path):
    media_root = str(settings.MEDIA_ROOT).replace("\\", "/")
    abs_path   = str(abs_path).replace("\\", "/")
    if abs_path.startswith(media_root):
        relative = abs_path[len(media_root):].lstrip("/")
        return settings.MEDIA_URL.rstrip("/") + "/" + relative
    return abs_path


# ─────────────────────────────────────────────
# Stage 1 — Generate Audio
# ─────────────────────────────────────────────

@login_required
def generate_audio(request):
    if request.method != "POST":
        return redirect("dashboard")

    t0        = time.perf_counter()
    text      = request.POST.get("text", "").strip()
    language  = request.POST.get("language", "en")
    avatar_id = request.POST.get("avatar_id", "").strip()
    avatar_type = request.POST.get("avatar_type", "platform").strip()  # "platform" or "user"

    logger.info("[generate_audio] user=%s lang=%s avatar_id=%s avatar_type=%s",
                request.user.username, language, avatar_id, avatar_type)

    if not text:
        messages.error(request, "Please enter some text before generating audio.")
        return redirect("dashboard")

    # ── Handle quick_upload: save UserAvatar first, then treat as user avatar ──
    if avatar_type == "quick_upload":
        from .models import UserAvatar

        quick_file = request.FILES.get("quick_avatar_file")
        quick_name = request.POST.get("quick_avatar_name", "").strip() or "My Avatar"

        if not quick_file:
            messages.error(request, "Please select a photo or video file to upload.")
            return redirect("dashboard")

        IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
        VIDEO_TYPES = {"video/mp4", "video/quicktime", "video/webm"}
        file_ct     = quick_file.content_type or ""

        is_image = file_ct in IMAGE_TYPES
        is_video = file_ct in VIDEO_TYPES

        if not is_image and not is_video:
            messages.error(request,
                "Unsupported file type. Please upload a JPG/PNG/WEBP photo or MP4/MOV/WebM video.")
            return redirect("dashboard")

        MAX_MB = 10 if is_image else 200
        if quick_file.size > MAX_MB * 1024 * 1024:
            messages.error(request,
                f"File exceeds the {MAX_MB} MB limit for {'photos' if is_image else 'videos'}.")
            return redirect("dashboard")

        try:
            ua = UserAvatar(
                owner         = request.user,
                name          = quick_name,
                category      = "custom",
                is_public     = False,
                review_status = "approved",
            )
            if is_video:
                ua.source_video = quick_file
            else:
                # For images: store as preview_image; source_video will be
                # set by the pipeline (image → video conversion happens there)
                ua.preview_image = quick_file
                ua.source_video  = quick_file   # pipeline receives the image path
            ua.save()
            avatar_id   = str(ua.pk)
            avatar_type = "user"
            logger.info("[generate_audio] quick_upload saved | user=%s ua_pk=%s type=%s",
                        request.user.username, ua.pk, "image" if is_image else "video")
        except Exception as exc:
            logger.error("[generate_audio] quick_upload failed | user=%s | %s",
                         request.user.username, exc, exc_info=True)
            messages.error(request, "Avatar upload failed. Please try again.")
            return redirect("dashboard")

    if not avatar_id:
        messages.error(request, "Please select an avatar before generating.")
        return redirect("dashboard")

    # ── Resolve avatar ────────────────────────
    from .models import Avatar, UserAvatar

    avatar_obj  = None   # platform Avatar instance (or None for user avatar)
    avatar_name = ""

    if avatar_type == "user":
        try:
            ua = UserAvatar.objects.get(pk=avatar_id, owner=request.user, is_active=True)
            if not ua.is_usable:
                messages.error(request, "That avatar is not available yet. Please choose another.")
                return redirect("dashboard")
            avatar_name = ua.name
            # Store user-avatar pk in session; avatar_obj stays None
        except UserAvatar.DoesNotExist:
            messages.error(request, "The selected avatar is not available. Please choose another.")
            return redirect("dashboard")
    else:
        try:
            avatar_obj  = Avatar.objects.get(pk=avatar_id, is_active=True)
            avatar_name = avatar_obj.name
        except Avatar.DoesNotExist:
            messages.error(request, "The selected avatar is not available. Please choose another.")
            return redirect("dashboard")

    # ── TTS ───────────────────────────────────
    try:
        t_tts          = time.perf_counter()
        audio_abs_path = generate_tts(text, language)
        _log_step("generate_audio:tts", t_tts, f"lang={language}")
    except Exception as exc:
        logger.error("[generate_audio] TTS failed | user=%s | %s",
                     request.user.username, exc, exc_info=True)
        messages.error(request, f"Audio generation failed: {exc}")
        return redirect("dashboard")

    try:
        audio_url = path_to_url(audio_abs_path)
    except Exception as exc:
        logger.error("[generate_audio] path_to_url failed | %s", exc)
        audio_url = str(audio_abs_path)

    # ── Save to session ───────────────────────
    request.session["text"]           = text
    request.session["language"]       = language
    request.session["audio_abs_path"] = str(audio_abs_path)
    request.session["audio_url"]      = audio_url
    request.session["avatar_id"]      = avatar_id
    request.session["avatar_type"]    = avatar_type

    _log_step("generate_audio:total", t0,
              f"user={request.user.username} lang={language} avatar={avatar_name}")

    return render(request, "video_app/result.html", {
        "audio_path":  audio_url,
        "avatar_name": avatar_name,
        "avatar":      avatar_obj,   # None for user-avatars (template should handle)
    })


# ─────────────────────────────────────────────
# Translation API
# ─────────────────────────────────────────────

def translate_api(request):
    t0   = time.perf_counter()
    text = request.GET.get("text", "").strip()
    lang = request.GET.get("lang", "")

    logger.info("[translate_api] lang=%s text_len=%d", lang, len(text))

    if not text or not lang:
        return JsonResponse({"error": "Both 'text' and 'lang' parameters are required."}, status=400)

    try:
        translated = translate_text(text, lang)
        _log_step("translate_api", t0, f"lang={lang}")
        return JsonResponse({"translated_text": translated})
    except Exception as exc:
        logger.error("[translate_api] failed | lang=%s | %s", lang, exc, exc_info=True)
        return JsonResponse({"error": f"Translation failed: {exc}"}, status=500)


# ─────────────────────────────────────────────
# Legacy redirect
# ─────────────────────────────────────────────

@login_required
def upload_avatar(request):
    """Legacy URL — redirect to the new avatar library."""
    return redirect("avatar_library")


# ─────────────────────────────────────────────
# Stage 2 — Process Avatar & Run Pipeline
# ─────────────────────────────────────────────

@login_required
def process_avatar(request):
    """
    Runs the Wav2Lip pipeline.
    Supports both platform Avatar and user-uploaded UserAvatar.
    Avatar type is determined from POST data or the session.
    """
    if request.method != "POST":
        return redirect("avatar_library")

    t0 = time.perf_counter()
    from .models import VideoGeneration, Avatar, UserAvatar

    # ── Resolve avatar id + type ──────────────
    avatar_id   = request.POST.get("avatar_id")   or request.session.get("avatar_id")
    avatar_type = request.POST.get("avatar_type") or request.session.get("avatar_type", "platform")

    if not avatar_id:
        messages.error(request, "No avatar selected. Please choose one and generate audio first.")
        return redirect("dashboard")

    # ── Resolve avatar object + source path ───
    avatar_path  = None
    avatar_name  = ""
    avatar_fk    = None   # platform Avatar FK for VideoGeneration (None for UserAvatar)

    if avatar_type == "user":
        try:
            ua = UserAvatar.objects.get(pk=avatar_id, owner=request.user, is_active=True)
            if not ua.is_usable:
                messages.error(request, f"'{ua.name}' is not available. Please choose another.")
                return redirect("avatar_library")
            avatar_path = ua.source_video_path
            avatar_name = ua.name
        except UserAvatar.DoesNotExist:
            messages.error(request, "That user avatar was not found.")
            return redirect("avatar_library")
    else:
        try:
            av = Avatar.objects.get(pk=avatar_id, is_active=True)
            avatar_path = av.source_video_path
            avatar_name = av.name
            avatar_fk   = av
        except Avatar.DoesNotExist:
            messages.error(request, "The selected avatar is not available.")
            return redirect("avatar_library")

    if not avatar_path or not os.path.exists(avatar_path):
        logger.error("[process_avatar] source video missing | avatar=%s path=%s",
                     avatar_name, avatar_path)
        messages.error(request,
            f"Source video for '{avatar_name}' not found on disk. Please contact support.")
        return redirect("avatar_library")

    # ── Validate session data ─────────────────
    text     = request.session.get("text")
    language = request.session.get("language")

    if not text or not language:
        logger.warning("[process_avatar] missing session | user=%s", request.user.username)
        messages.error(request, "Session expired. Please generate audio again.")
        return redirect("dashboard")

    logger.info("[process_avatar] user=%s avatar=%s type=%s lang=%s",
                request.user.username, avatar_name, avatar_type, language)

    # ── Run ML pipeline ───────────────────────
    try:
        t_pipe         = time.perf_counter()
        video_abs_path = run_pipeline(text, language, avatar_path)
        _log_step("process_avatar:pipeline", t_pipe, f"lang={language} avatar={avatar_name}")
    except Exception as exc:
        logger.error("[process_avatar] pipeline failed | user=%s | %s",
                     request.user.username, exc, exc_info=True)

        VideoGeneration.objects.create(
            user        = request.user,
            language    = language,
            input_text  = text,
            audio_file  = request.session.get("audio_abs_path", ""),
            avatar      = avatar_fk,
            avatar_name = avatar_name,
            status      = "failed",
            duration_s  = round(time.perf_counter() - t0, 2),
        )

        messages.error(request, f"Video generation failed: {exc}. Please try again.")
        return redirect("avatar_library")

    # ── Resolve URLs ──────────────────────────
    try:
        video_url = path_to_url(video_abs_path)
    except Exception as exc:
        logger.error("[process_avatar] path_to_url failed | %s", exc)
        video_url = str(video_abs_path)

    audio_url = request.session.get("audio_url", "")

    # ── Relative paths for DB ─────────────────
    media_root = str(settings.MEDIA_ROOT).replace("\\", "/")

    video_rel = str(video_abs_path).replace("\\", "/")
    if video_rel.startswith(media_root):
        video_rel = video_rel[len(media_root):].lstrip("/")

    audio_rel = str(request.session.get("audio_abs_path", "")).replace("\\", "/")
    if audio_rel.startswith(media_root):
        audio_rel = audio_rel[len(media_root):].lstrip("/")

    total_secs = round(time.perf_counter() - t0, 2)

    # ── Save successful record ────────────────
    VideoGeneration.objects.create(
        user        = request.user,
        language    = language,
        input_text  = text,
        audio_file  = audio_rel,
        video_file  = video_rel,
        avatar      = avatar_fk,
        avatar_name = avatar_name,
        status      = "done",
        duration_s  = total_secs,
    )

    _log_step("process_avatar:total", t0,
              f"user={request.user.username} video={video_url}")

    return render(request, "video_app/video_processing.html", {
        "video_path":  video_url,
        "audio_path":  audio_url,
        "avatar_name": avatar_name,
        "avatar":      avatar_fk,   # None for user-avatars
    })