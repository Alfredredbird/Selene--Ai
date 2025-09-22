import speech_recognition as sr
import datetime
import os

def listen():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        try:
            print("Listening...")
            audio = recognizer.listen(source, timeout=5)

            # Create timestamped filename to avoid overwriting
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            folder = "data/samples"
            os.makedirs(folder, exist_ok=True)
            wav_path = os.path.join(folder, f"note_{timestamp}.wav")

            # Save audio data to WAV file
            with open(wav_path, "wb") as f:
                f.write(audio.get_wav_data())

            # Recognize speech from audio
            command = recognizer.recognize_google(audio)
            return command.lower(), wav_path

        except (sr.UnknownValueError, sr.WaitTimeoutError):
            print("Could not understand.")
            return None, None
