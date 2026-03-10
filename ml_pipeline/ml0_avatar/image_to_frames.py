import cv2
import os


def image_to_frames(image_path, output_dir, frames=100):

    os.makedirs(output_dir, exist_ok=True)

    img = cv2.imread(image_path)

    for i in range(frames):

        frame_name = f"frame_{i:04d}.png"
        frame_path = os.path.join(output_dir, frame_name)

        cv2.imwrite(frame_path, img)

    return output_dir