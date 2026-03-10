from gtts import gTTS
import os
import uuid
from django.conf import settings


def generate_audio(text, lang):

    # save inside outputs/audio
    output_dir = os.path.join(settings.MEDIA_ROOT, "audio")

    os.makedirs(output_dir, exist_ok=True)

    filename = f"{uuid.uuid4()}.mp3"

    audio_path = os.path.join(output_dir, filename)

    tts = gTTS(text=text, lang=lang)
    tts.save(audio_path)

    print("Audio saved at:", audio_path)

    # return URL path
    return f"{settings.MEDIA_URL}audio/{filename}"