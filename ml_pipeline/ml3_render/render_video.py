import os
import subprocess

def render_video(frames_dir, audio_path, output_path):

    print("Rendering final video...")

    cmd = [
        "ffmpeg",
        "-y",
        "-r", "25",
        "-i", f"{frames_dir}/frame_%04d.png",
        "-i", audio_path,
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        output_path
    ]

    subprocess.run(cmd)

    print("Video rendered:", output_path)

    return output_path