from googletrans import Translator

translator = Translator()

def translate_text(text,target_lang):

    translated = translator.translate(text,dest=target_lang)

    return translated.text