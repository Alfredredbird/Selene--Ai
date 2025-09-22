from functions.recorder import start_audio_recording, start_screen_recording, stop_all_recording, clip_last_30_seconds, start_recording

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
from functions.recorder import *

WAKE_WORDS = ["Luna", "luna", "loona", "luna"]
NAME = "Luna"
WAKE_PHRASES = [f"hey {NAME}", f"hello {NAME}", f"good day {NAME}"]

def main():
    cleanup_old_recordings()
    cleanup_old_recordings("data/voice_clips")
    cleanup_old_recordings("data/screen_recordings")
    # this is for the screen clipping. its laggy so its disabled now
    # start_recording()
    # print("[INFO] Background recording started.")

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
                    if "bye" in command or "exit" in command or "quit" in command or "goodbye" in command:
                        exit(1) 
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
