from functions.stt import listen
from functions.tts import speak
from functions.commands import handle_command
from functions.functions import cleanup_old_recordings, scan_ble, extract_song_metadata
from functions.identify import identify_speaker  
import asyncio
import threading
from functions.tts import *
from functions.stt import *
from functions.security import *


WAKE_WORDS = ["selene", "celine", "saline", "selena"]
NAME = "Selene"
WAKE_PHRASES = [f"hey {NAME}", f"hello {NAME}", f"good day {NAME}"]

def main():
    cleanup_old_recordings()

    if not collect_system_info():
        pass 

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

            # Check if any wake word is in the command
            detected_wake_word = next((word for word in WAKE_WORDS if word in command), None)

            if detected_wake_word:
                # Remove the wake word from the command
                command = command.replace(detected_wake_word, "").strip()

                if command:
                    response = handle_command(command, NAME, speaker_name)
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
