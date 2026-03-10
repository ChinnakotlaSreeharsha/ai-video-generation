import os
import subprocess
import sys
from django.conf import settings


def run_wav2lip(audio_path, avatar_path, output_dir):

    print("Running Wav2Lip model...")

    os.makedirs(output_dir, exist_ok=True)

    project_root = os.path.dirname(settings.BASE_DIR)

    wav2lip_script = os.path.join(
        project_root,
        "ml_pipeline",
        "wav2lip",
        "inference.py"
    )

    model_path = os.path.join(
        project_root,
        "ml_pipeline",
        "models",
        "wav2lip_gan.pth"
    )

    output_video = os.path.join(output_dir, "lipsynced.mp4")

    cmd = [
        sys.executable,
        wav2lip_script,
        "--checkpoint_path", model_path,
        "--face", avatar_path,
        "--audio", audio_path,
        "--outfile", output_video,
        "--pads", "0", "10", "0", "0",
        "--resize_factor", "1"
    ]

    print("Executing command:")
    print(" ".join(cmd))

    process = subprocess.Popen(
        cmd,
        cwd=os.path.join(project_root, "ml_pipeline", "wav2lip"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    stdout, stderr = process.communicate()

    print("========== WAV2LIP STDOUT ==========")
    print(stdout)

    print("========== WAV2LIP STDERR ==========")
    print(stderr)

    # If Wav2Lip failed, return the error text instead of crashing Django
    if process.returncode != 0:
        print("Wav2Lip failed. See STDERR above.")
        return None

    print("Wav2Lip finished successfully")

    return output_video