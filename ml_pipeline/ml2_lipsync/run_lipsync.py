import os
import shutil

def run_lipsync(audio_path, frames_dir, output_dir):

    print("Running LipSync...")

    os.makedirs(output_dir, exist_ok=True)

    for frame in os.listdir(frames_dir):

        src = os.path.join(frames_dir, frame)
        dst = os.path.join(output_dir, frame)

        shutil.copy(src, dst)

    print("LipSync completed")

    return output_dir