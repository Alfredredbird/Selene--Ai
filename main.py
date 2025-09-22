from functions.stt import listen
from .functionstts import speak
from commands import handle_command
from functions import cleanup_old_recordings, scan_ble, extract_song_metadata
from identify import identify_speaker  
import asyncio
import threading
from functions.tts import *
from functools.stt import *

WAKE_WORD = "selene"
WAKE_WORD2 = "selene"
NAME = "Selene"
WAKE_PHRASE = f"hey {NAME}"
WAKE_PHRASE2 = f"hello {NAME}"
WAKE_PHRASE3 = f"good day {NAME}"

def main():
    cleanup_old_recordings()
    try:
        speak("Hello! I'm your voice assistant.", True)
        while True:
            extract_song_metadata("data/music/", "config/songs_metadata.json")
            print("Waiting for wake word...")

            command, wav_path = listen()
            if not command or not wav_path:
                continue

            # Run speaker recognition
            speaker_name = identify_speaker(wav_path)

            if speaker_name:
                print(f"Recognized speaker: {speaker_name}")
            else:
                print("Unknown speaker.")


            print("=====================================")
            print(f"Heard: {command}")
            print("=====================================")

            if WAKE_WORD in command or WAKE_WORD2 in command:
                command = command.replace(WAKE_WORD, "").replace(WAKE_WORD2, "").strip()
                if command:
                    response = handle_command(command, NAME,speaker_name)
                    speak(response, True)
                else:
                    if speaker_name:
                     speak(f"Yes {speaker_name}?", True)
                    else:
                     speak("Yes?", True)
            else:
                print("Wake word not detected.")
            cleanup_old_recordings()

    except KeyboardInterrupt:
        print("Assistant stopped by user.")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()
