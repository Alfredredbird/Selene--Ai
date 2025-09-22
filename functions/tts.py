import os
import json
from datetime import datetime
from TTS.api import TTS

# Paths
AUDIO_FOLDER = "audios"
CONFIG_FOLDER = "config"
CACHE_FILE = os.path.join(CONFIG_FOLDER, "audio_cache.json")

# Setup folders
os.makedirs(AUDIO_FOLDER, exist_ok=True)
os.makedirs(CONFIG_FOLDER, exist_ok=True)

# Load or initialize cache
if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "r") as f:
        audio_cache = json.load(f)
else:
    audio_cache = {}

# Initialize model
tts_model = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC", progress_bar=False)

def text_to_filename(text):
    return text.lower().strip().replace(" ", "_").replace("?", "").replace("!", "").replace(",", "").replace("'", "").replace(".", "").replace("[", "").replace("]", "").replace("(", "").replace(")", "") + ".wav"

def speak(text, save):
    print("Assistant:", text)
    key = text.strip()

    if save:
        if key in audio_cache:
            entry = audio_cache[key]
            path = entry["path"]
            created = entry["created"]
            print(f"Using cached audio: {path} (Created on {created})")
        else:
            filename = text_to_filename(key)
            path = os.path.join(AUDIO_FOLDER, filename)
            print(f"Generating audio for: '{key}'")
            tts_model.tts_to_file(text=key, file_path=path)

            # Save to cache with date
            created_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            audio_cache[key] = {
                "path": path,
                "created": created_date
            }
            with open(CACHE_FILE, "w") as f:
                json.dump(audio_cache, f, indent=2)
    else:
        path = "cache/recording.wav"
        print(f"Generating temporary audio for: '{key}'")
        tts_model.tts_to_file(text=key, file_path=path)

    os.system(f"aplay {path}")
