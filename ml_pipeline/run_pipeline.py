import os
from django.conf import settings

from ml_pipeline.ml1_tts.process_tts import generate_tts
from ml_pipeline.ml0_avatar.extract_frames import extract_frames
from ml_pipeline.ml0_avatar.image_to_frames import image_to_frames
from ml_pipeline.ml2_lipsync.run_wav2lip import run_wav2lip


def run_pipeline(text, language, avatar_path):

    print("===== AI VIDEO PIPELINE START =====")

    media_root = settings.MEDIA_ROOT

    # -----------------------------
    # Stage 1 : Generate Audio
    # -----------------------------
    print("Step 1: Generating TTS")

    audio_url = generate_tts(text, language)

    audio_file = os.path.join(
        media_root,
        "audio",
        os.path.basename(audio_url)
    )

    print("Audio generated:", audio_file)

    # -----------------------------
    # Stage 2 : Prepare Avatar
    # -----------------------------
    print("Step 2: Preparing Avatar")

    frames_dir = os.path.join(media_root, "frames")
    os.makedirs(frames_dir, exist_ok=True)

    filename = avatar_path.lower()

    if filename.endswith((".mp4", ".mov", ".avi")):
        print("Extracting frames from video avatar...")
        extract_frames(avatar_path, frames_dir)
    else:
        print("Creating frames from image avatar...")
        image_to_frames(avatar_path, frames_dir)

    print("Avatar preparation complete")

    # -----------------------------
    # Stage 3 : LipSync
    # -----------------------------
    print("Step 3: Running Wav2Lip")

    lipsync_dir = os.path.join(media_root, "lipsync")
    os.makedirs(lipsync_dir, exist_ok=True)

    lipsynced_video = run_wav2lip(
        audio_path=audio_file,
        avatar_path=avatar_path,   # corrected
        output_dir=lipsync_dir
    )

    print("LipSync completed:", lipsynced_video)

    # -----------------------------
    # Stage 4 : Final Output
    # -----------------------------
    print("Step 4: Final video ready")

    print("===== PIPELINE COMPLETE =====")

    return lipsynced_video