from .translator import translate_text
from .tts_engine import generate_audio


def generate_tts(text,language):

    print("Step 1: Translating Text")

    translated_text = translate_text(text,language)

    print("Step 2: Generating TTS")

    audio_path = generate_audio(translated_text,language)

    print("Audio Generated:",audio_path)

    return audio_path