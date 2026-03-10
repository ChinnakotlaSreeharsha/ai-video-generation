import cv2
import os


def extract_frames(video_path, output_dir):

    os.makedirs(output_dir, exist_ok=True)

    cap = cv2.VideoCapture(video_path)

    frame_count = 0

    while True:
        ret, frame = cap.read()

        if not ret:
            break

        frame_name = f"frame_{frame_count:04d}.png"
        frame_path = os.path.join(output_dir, frame_name)

        cv2.imwrite(frame_path, frame)

        frame_count += 1

    cap.release()

    print(f"{frame_count} frames extracted")

    return output_dir