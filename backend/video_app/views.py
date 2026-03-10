from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
import os

from ml_pipeline.ml1_tts.process_tts import generate_tts
from ml_pipeline.ml1_tts.translator import translate_text
from ml_pipeline.run_pipeline import run_pipeline


def index(request):
    return render(request, "video_app/index.html")


def dashboard(request):
    return render(request, "video_app/dashboard.html")


# ─────────────────────────────────────────────
# HELPER: convert absolute file path → browser URL
# e.g. /home/user/project/outputs/audio/file.mp3
#   →  /outputs/audio/file.mp3
# ─────────────────────────────────────────────
def path_to_url(abs_path):
    """
    MEDIA_ROOT  = BASE_DIR / 'outputs'   (e.g. /home/user/project/outputs)
    MEDIA_URL   = '/outputs/'

    This strips MEDIA_ROOT from the absolute path and prepends MEDIA_URL.
    """
    media_root = str(settings.MEDIA_ROOT)
    abs_path   = str(abs_path)

    # Normalise separators on Windows
    media_root = media_root.replace("\\", "/")
    abs_path   = abs_path.replace("\\", "/")

    if abs_path.startswith(media_root):
        relative = abs_path[len(media_root):]          # e.g. /audio/file.mp3
        relative = relative.lstrip("/")                # strip leading slash
        url = settings.MEDIA_URL.rstrip("/") + "/" + relative
        return url                                      # e.g. /outputs/audio/file.mp3

    # Fallback: return as-is (already a URL or unexpected path)
    return abs_path


# ─────────────────────────────────────────────
# Stage 1 : Generate Audio
# ─────────────────────────────────────────────
def generate_audio(request):

    if request.method == "POST":

        text     = request.POST.get("text")
        language = request.POST.get("language")

        # generate_tts() returns an absolute path like:
        # /home/.../outputs/audio/en_1234.mp3
        audio_abs_path = generate_tts(text, language)

        # ✅ FIX: convert to browser URL before passing to template
        audio_url = path_to_url(audio_abs_path)

        # Store BOTH for Stage 2
        request.session["text"]          = text
        request.session["language"]      = language
        request.session["audio_abs_path"] = str(audio_abs_path)  # pipeline needs abs path
        request.session["audio_url"]     = audio_url              # template needs URL

        return render(request, "video_app/result.html", {
            "audio_path": audio_url    # ✅ now a proper URL e.g. /outputs/audio/en_1234.mp3
        })


# ─────────────────────────────────────────────
# Translation API
# ─────────────────────────────────────────────
def translate_api(request):

    text = request.GET.get("text")
    lang = request.GET.get("lang")

    translated = translate_text(text, lang)

    return JsonResponse({
        "translated_text": translated
    })


# ─────────────────────────────────────────────
# Stage 2 UI — Avatar upload form
# ─────────────────────────────────────────────
def upload_avatar(request):
    return render(request, "video_app/upload_avatar.html")


# ─────────────────────────────────────────────
# Stage 2 Processing — runs pipeline, shows result
# ─────────────────────────────────────────────
def process_avatar(request):

    if request.method == "POST":

        avatar = request.FILES.get("avatar_file")

        # Save uploaded avatar inside MEDIA_ROOT/avatars/
        avatar_dir = os.path.join(settings.MEDIA_ROOT, "avatars")
        os.makedirs(avatar_dir, exist_ok=True)

        avatar_path = os.path.join(avatar_dir, avatar.name)

        with open(avatar_path, "wb+") as f:
            for chunk in avatar.chunks():
                f.write(chunk)

        print("Avatar saved:", avatar_path)

        # Retrieve text and language from session
        text     = request.session.get("text")
        language = request.session.get("language")

        # ✅ FIX: run_pipeline() now returns the output video path
        # Make sure run_pipeline returns the abs path of the generated video.
        # If it currently returns None or something else, see note below.
        video_abs_path = run_pipeline(text, language, avatar_path)

        print("Pipeline result:", video_abs_path)

        # ✅ FIX: convert video path → browser URL
        video_url = path_to_url(video_abs_path)

        # Get audio URL from session (set in generate_audio)
        audio_url = request.session.get("audio_url", "")

        # ✅ FIX: render video_processing.html (NOT video_processing.html)
        # video_processing.html is just a loading animation — it's not needed
        # when the pipeline runs synchronously (blocks until done, then redirects)
        return render(request, "video_app/video_processing.html", {
            "video_path": video_url,    # e.g. /outputs/videos/output_1234.mp4
            "audio_path": audio_url,    # e.g. /outputs/audio/en_1234.mp3
            "avatar":     avatar.name,
        })


# ─────────────────────────────────────────────
# Custom 404
# ─────────────────────────────────────────────
def page_not_found(request, exception=None):
    return render(request, "video_app/404.html", status=404)