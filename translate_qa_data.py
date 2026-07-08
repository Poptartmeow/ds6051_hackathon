import json
import time
from pathlib import Path

from deep_translator import GoogleTranslator
from deep_translator.exceptions import TranslationNotFound, RequestError, TooManyRequests

input_path = Path("qa_data_250.json")

spanish_output_path = Path("qa_data_250_spanish.json")
swahili_output_path = Path("qa_data_250_swahili.json")

fields_to_translate = [
    "knowledge",
    "question",
    "right_answer",
    "hallucinated_answer",
]

translator_es = GoogleTranslator(source="en", target="es")
translator_sw = GoogleTranslator(source="en", target="sw")  # Swahili


def safe_translate(translator, text, retries=3):
    """
    Translate text, but do not crash if translation fails.
    If translation fails, return the original English text.
    """
    if not text or not isinstance(text, str):
        return ""

    for attempt in range(retries):
        try:
            translated = translator.translate(text)

            # Sometimes proper nouns return None or empty strings
            if translated:
                return translated

            return text

        except TranslationNotFound:
            # Usually happens with names, bands, titles, or proper nouns
            return text

        except TooManyRequests:
            wait_time = 5 * (attempt + 1)
            print(f"Too many requests. Waiting {wait_time} seconds...")
            time.sleep(wait_time)

        except RequestError:
            wait_time = 3 * (attempt + 1)
            print(f"Request error. Retrying in {wait_time} seconds...")
            time.sleep(wait_time)

        except Exception as e:
            print(f"Unexpected translation error: {e}")
            return text

    return text


with input_path.open("r", encoding="utf-8") as f:
    data = json.load(f)

spanish_data = []
swahili_data = []

for i, entry in enumerate(data, start=1):
    spanish_entry = {}
    swahili_entry = {}

    for field in fields_to_translate:
        text = entry.get(field, "")

        spanish_entry[field] = safe_translate(translator_es, text)
        time.sleep(0.2)

        swahili_entry[field] = safe_translate(translator_sw, text)
        time.sleep(0.2)

    spanish_data.append(spanish_entry)
    swahili_data.append(swahili_entry)

    print(f"Translated {i}/{len(data)}")

    # Save progress after each entry so you don't lose everything if it stops
    with spanish_output_path.open("w", encoding="utf-8") as f:
        json.dump(spanish_data, f, indent=2, ensure_ascii=False)

    with swahili_output_path.open("w", encoding="utf-8") as f:
        json.dump(swahili_data, f, indent=2, ensure_ascii=False)

print(f"\nSaved Spanish file to {spanish_output_path}")
print(f"Saved Swahili file to {swahili_output_path}")
