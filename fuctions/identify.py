# speaker_profiles.py
from resemblyzer import VoiceEncoder, preprocess_wav
import numpy as np
import os
import soundfile as sf

encoder = VoiceEncoder()
profiles_dir = "data/profiles"



def save_voice_profile(name, wav_path):
    wav = preprocess_wav(wav_path)
    embed = encoder.embed_utterance(wav)
    np.save(os.path.join(profiles_dir, f"{name}.npy"), embed)
    return f"Voice profile for {name} saved."

from resemblyzer import preprocess_wav, VoiceEncoder
import numpy as np
import os

encoder = VoiceEncoder()
profiles_dir = "data/profiles"
SIMILARITY_THRESHOLD = 0.9  # Lower = more strict

def identify_speaker(wav_path):
    wav = preprocess_wav(wav_path)
    embed = encoder.embed_utterance(wav)
    print(f"[Debug] New embedding shape: {embed.shape}")

    closest_speaker = None
    closest_dist = float("inf")

    for file in os.listdir(profiles_dir):
        if file.endswith(".npy"):
            profile_path = os.path.join(profiles_dir, file)
            known_embed = np.load(profile_path)

            if embed.shape != known_embed.shape:
                print(f"[Warning] Shape mismatch for {file}, skipping")
                continue

            dist = np.linalg.norm(embed - known_embed)
            print(f"[Debug] Distance to {file}: {dist:.4f}")

            if dist < closest_dist:
                closest_dist = dist
                closest_speaker = file.replace(".npy", "")

    if closest_speaker and closest_dist < SIMILARITY_THRESHOLD:
        print(f"[Info] Closest match: {closest_speaker} (distance: {closest_dist:.4f})")
        return closest_speaker

    print("[Info] No recognized speaker found.")
    return None


