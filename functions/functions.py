import os
import wikipedia 
import multiprocessing
import json
import pexpect
import subprocess
import socket
from datetime import datetime, timedelta
from bleak import BleakScanner
import asyncio
import time
import re
from functions.tts import speak
from mutagen import File
import random
import sounddevice as sd
import soundfile as sf
import librosa
import numpy as np
import os
from resemblyzer import VoiceEncoder, preprocess_wav
from pydub import AudioSegment
from functions.stt import listen
import platform
import requests
import threading


CONFIG_FOLDER = "config"
CACHE_FILE = os.path.join(CONFIG_FOLDER, "audio_cache.json")
REMOTE_VERSION_URL = "https://raw.githubusercontent.com/Alfredredbird/Selene--Ai/refs/heads/master/config/version.cfg"
LOCAL_VERSION_PATH = "config/version.cfg"
BRANCH = "master"

SSH_LOG_FILE = "data/ssh_connections.json"

def getFiles(directory_path):
    try:
        files = [
            os.path.splitext(f)[0]
            for f in os.listdir(directory_path)
            if os.path.isfile(os.path.join(directory_path, f))
        ]
        return files
    except FileNotFoundError:
        return f"Error: Directory '{directory_path}' not found."
    except NotADirectoryError:
        return f"Error: '{directory_path}' is not a directory."
    except Exception as e:
        return f"An unexpected error occurred: {e}"

def searchWikipedia(index):
    try:
        result = wikipedia.summary(index, sentences=1)
        print(result)
        return result
    except wikipedia.exceptions.DisambiguationError as e:
        return f"Your query is ambiguous, please be more specific. Options include: {e.options[:5]}"
    except wikipedia.exceptions.PageError:
        return "Sorry, I could not find any information on Wikipedia for that topic."
    except Exception as e:
        return f"An error occurred while searching Wikipedia: {str(e)}"
    

def load_servers_config(path="config/servers.json"):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading servers.json: {e}")
        return {}

def check_server_status(name):
    servers = load_servers_config()
    ip = servers.get(name.lower())

    if not ip:
        return f"I don't know a server named {name}."

    try:
        print(f"Pinging {name} at {ip}...")
        result = subprocess.run(["ping", "-c", "3", ip], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode == 0:
            return f"{name} is on line and reachable."
        else:
            return f"{name} seems to be off line or unreachable."
    except Exception as e:
        return f"Error checking {name}: {str(e)}"


def get_local_ip():
    try:
        # Connect to an external address (doesnt actually send data)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception as e:
        return f"Error: {e}"

def cleanup_old_recordings(days_unused=5):
    if not os.path.exists(CACHE_FILE):
        print("Cache file not found.")
        return

    with open(CACHE_FILE, "r") as f:
        audio_cache = json.load(f)

    now = datetime.now()
    threshold = now - timedelta(days=days_unused)
    keys_to_delete = []

    for key, entry in audio_cache.items():
        try:
            created = datetime.strptime(entry["created"], "%Y-%m-%d %H:%M:%S")
            if created < threshold:
                path = entry["path"]
                if os.path.exists(path):
                    os.remove(path)
                    print(f"Deleted old audio file: {path}")
                keys_to_delete.append(key)
        except Exception as e:
            print(f"Error parsing entry '{key}': {e}")

    for key in keys_to_delete:
        del audio_cache[key]

    # Save updated cache
    with open(CACHE_FILE, "w") as f:
        json.dump(audio_cache, f, indent=2)

    print(f"Cleanup complete. {len(keys_to_delete)} old entries removed.")


async def scan_ble():
    print("Scanning for BLE devices...")
    devices = await BleakScanner.discover(timeout=5)
    for d in devices:
        print("=================================")
        print(f"{d.address} - {d.name} (RSSI: {d.rssi})")
        print("=================================")


def close_application(app_name, force=False):
    system = platform.system()
    try:
        if system in ["Darwin", "Linux"]:  # macOS or Linux
            # Use pgrep to find process IDs case-insensitively
            pgrep_cmd = ["pgrep", "-i", app_name]
            proc = subprocess.run(pgrep_cmd, capture_output=True, text=True)
            pids = proc.stdout.split()
            
            if not pids:
                return f"No running process found for {app_name} on {system}."
            
            for pid in pids:
                kill_cmd = ["kill"]
                if force:
                    kill_cmd.append("-9")
                kill_cmd.append(pid)
                subprocess.run(kill_cmd)
            
            return f"Closing {app_name}{' forcefully' if force else ''} on {system}."
        
        elif system == "Windows":
            cmd = ["taskkill", "/IM", f"{app_name}.exe"]
            if force:
                cmd.append("/F")
            subprocess.run(cmd, shell=True)
            return f"Closing {app_name}{' forcefully' if force else ''} on Windows."
        
        else:
            return f"Sorry, closing apps is not supported on {system}."

    except Exception as e:
        return f"Failed to close {app_name}: {e}"

def bluetooth_connect_worker(index, devices):
    try:
        if index < 0 or index >= len(devices):
            return f"Invalid device number. Please choose between 1 and {len(devices)}."
        
        device = devices[index]
        mac = device["mac"]

        child = pexpect.spawn("bluetoothctl", timeout=10)
        child.expect("#")

        child.sendline("power on")
        child.expect("#")

        child.sendline(f"connect {mac}")
        idx = child.expect(["Connection successful", "Failed to connect", pexpect.EOF, pexpect.TIMEOUT], timeout=10)

        output = child.before.decode().strip()
        child.sendline("exit")

        if idx == 0:  # "Connection successful"
            return f"Connected successfully to {device['name']} ({mac})."
        else:
            return f"Failed to connect to {device['name']} ({mac}). Output: {output}"

    except Exception as e:
        return f"Bluetooth connection failed: {e}"


def parse_minutes_from_command(command):
    # Map words to numbers
    words_to_numbers = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10
    }

    match = re.search(r"(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+minute", command)
    if match:
        val = match.group(1)
        return int(val) if val.isdigit() else words_to_numbers.get(val, 1)
    return None


def extract_song_metadata(folder_path, output_json):
    supported_formats = ('.mp3', '.wav', '.flac', '.ogg', '.m4a')
    songs_metadata = []

    # Load existing metadata if file exists
    if os.path.exists(output_json):
        try:
            with open(output_json, 'r') as f:
                existing_metadata = {entry["filename"]: entry for entry in json.load(f)}
        except Exception:
            existing_metadata = {}
    else:
        existing_metadata = {}

    for filename in os.listdir(folder_path):
        if filename.lower().endswith(supported_formats):
            filepath = os.path.join(folder_path, filename)
            audio = File(filepath)
            if audio is None:
                continue

            length = int(audio.info.length) if hasattr(audio, 'info') else 0

            # Only set genre if not already set
            if filename in existing_metadata and existing_metadata[filename].get("genre"):
                genre = existing_metadata[filename]["genre"]
            else:
                genre = ""
                if audio.tags:
                    for key in audio.tags.keys():
                        if 'genre' in key.lower():
                            genre = str(audio.tags[key])
                            break

            songs_metadata.append({
                "filename": filename,
                "length": length,
                "genre": genre
            })

    # Save updated metadata
    with open(output_json, 'w') as json_file:
        json.dump(songs_metadata, json_file, indent=4)

    print(f"Metadata extracted and saved to {output_json}")


    print(f"Metadata extracted and saved to {output_json}")




encoder = VoiceEncoder()

def record_and_save_voice_profile(name, duration=10, samplerate=44100):
    os.makedirs("data/profiles", exist_ok=True)
    temp_wav_path = f"data/profiles/{name}_temp.wav"

    print(f"Recording voice profile for {name}...")
    recording = sd.rec(int(samplerate * duration), samplerate=samplerate, channels=1)
    sd.wait()
    sf.write(temp_wav_path, recording, samplerate)

    # Preprocess and embed with Resemblyzer
    wav = preprocess_wav(temp_wav_path)
    embed = encoder.embed_utterance(wav)

    # Save embedding (shape should be 256)
    np.save(os.path.join("data/profiles", f"{name}.npy"), embed)

    os.remove(temp_wav_path)
    print(f"Voice profile for {name} saved using Resemblyzer embeddings.")
    return f"Voice profile for {name} saved using Resemblyzer embeddings."

def cleanup_old_recordings(folder="data/samples", max_age_seconds=60):
    now = time.time()
    for filename in os.listdir(folder):
        if filename.endswith(".wav"):
            filepath = os.path.join(folder, filename)
            file_age = now - os.path.getmtime(filepath)
            if file_age > max_age_seconds:
                try:
                    os.remove(filepath)
                    print(f"Deleted old recording: {filename}")
                except Exception as e:
                    print(f"Error deleting {filename}: {e}")

def detect_voice(audio, threshold=0.01):
    """Returns True if voice activity is detected based on RMS energy."""
    energy = np.sqrt(np.mean(audio**2))
    return energy > threshold



def open_application(app_name):
    system = platform.system()

    try:
        if system == "Darwin":  # macOS
            subprocess.Popen(["open", "-a", app_name])
            return f"Opening {app_name} on macOS."
        
        elif system == "Windows":
           
            subprocess.Popen(["start", "", app_name], shell=True)
            return f"Opening {app_name} on Windows."
        
        elif system == "Linux":  # Ubuntu or others
           
            try:
                subprocess.Popen([app_name])
            except FileNotFoundError:
                subprocess.Popen(["xdg-open", app_name])
            return f"Opening {app_name} on Linux."
        
        else:
            return f"Sorry, opening apps is not supported on {system}."
    
    except Exception as e:
        return f"Failed to open {app_name}: {e}"


def open_directory(command):
    """
    Opens common directories based on the command.
    """
    home = os.path.expanduser("~")
    directories = {
        "home": home,
        "downloads": os.path.join(home, "Downloads"),
        "documents": os.path.join(home, "Documents"),
        "pictures": os.path.join(home, "Pictures"),
        "videos": os.path.join(home, "Videos"),
        "public": os.path.join(home, "Public"),
        "templates": os.path.join(home, "Templates"),
        "snap": os.path.join(home, "snap"),
        "desktop": os.path.join(home, "Desktop")
    }

    command = command.lower().strip()
    for key, path in directories.items():
        if key in command:
            if os.path.exists(path):
                subprocess.Popen(["xdg-open", path])
                return f"Opening {key} folder."
            else:
                return f"{key.capitalize()} folder does not exist."
    return "I couldn't recognize which folder to open."


def record_phrase(prompt, filename, max_retries=3, duration=4, samplerate=44100):
    retries = 0
    while retries < max_retries:
        print(f"\nSay: \"{prompt}\" (waiting for your voice...)")
        recording = sd.rec(int(samplerate * duration), samplerate=samplerate, channels=1)
        sd.wait()

        if detect_voice(recording):
            sf.write(filename, recording, samplerate)
            print(f"Recorded: {prompt}")
            return True
        else:
            print("Didn't catch that. Let's try again.")
            retries += 1
            time.sleep(1)

    print(f"Failed to record phrase after {max_retries} attempts.")
    return False

def combine_audio(files, output_file):
    combined = AudioSegment.empty()
    for file in files:
        segment = AudioSegment.from_wav(file)
        combined += segment
    combined.export(output_file, format="wav")
    print(f"Combined audio saved to: {output_file}")

def create_combined_voice_sample(name, systemname):
    os.makedirs("data/profiles", exist_ok=True)
    phrase_prompts = [
        f"{systemname} what time is it",
        f"{systemname} search wikipedia",
        f"{systemname} play rap music",
        f"{systemname} skip",
        f"{systemname} music list",
        f"{systemname} how is moon base",
        f"{systemname} how are you doing"
    ]
    recorded_files = []
    speak("To get to know you better, I will provide you with a few sentances to read.", True)
    time.sleep(0.5)
    speak("repeat after me!", True)
    for i, phrase in enumerate(phrase_prompts):
        speak(phrase, True)
        file_path = f"data/profiles/{name}_phrase_{i}.wav"
        success = record_phrase(phrase, file_path)
        if not success:
            print("Aborting voice profile creation.")
            return
        recorded_files.append(file_path)

    combined_path = f"data/profiles/{name}_combined.wav"
    combine_audio(recorded_files, combined_path)

    # Create and save the voice embedding
    wav = preprocess_wav(combined_path)
    embed = encoder.embed_utterance(wav)
    np.save(os.path.join("data/profiles", f"{name}.npy"), embed)

    # Clean up individual phrase files
    for file in recorded_files:
        os.remove(file)

    print(f"Voice profile for {name} saved using Resemblyzer embeddings.")
    return f"Voice profile for {name} saved."


def trivia_game():
    trivia_file = "config/trivia.json"
    if not os.path.exists(trivia_file):
        return "Trivia questions file not found."

    with open(trivia_file, "r") as f:
        trivia = json.load(f)

    random.shuffle(trivia)
    trivia = trivia[:5]  # Pick 5 random questions

    total = len(trivia)
    correct = 0

    speak("Let's play a trivia game! Answer the questions as best you can.", True)

    for q in trivia:
        question = q[0]   
        answer = q[1]    

        speak(question, True)
        user_answer, audio_path = listen()
        if not user_answer:
            speak("I didn't catch that. Let's move to the next question.", True)
            continue

        user_answer = user_answer.lower().strip()  # Now this is safe: user_answer is a string
        expected = answer.lower().strip()

        if expected in user_answer:
            correct += 1
            speak("Correct!", True)
        else:
            speak(f"Wrong. The correct answer was {answer}.", True)

    accuracy = correct / total if total > 0 else 0
    result = f"You got {correct} out of {total} correct. That's {int(accuracy * 100)} percent."

    if accuracy >= 0.8:
        speak(result + " You win!", True)
        return "You passed the trivia challenge!"
    else:
        speak(result + " You lose!", True)
        return "Try again next time!"
    
def check_for_updates():
    """Check remote vs local version, pull updates if needed."""
    try:
        # Fetch remote version
        remote_version = requests.get(REMOTE_VERSION_URL, timeout=5).text.strip()

        # Read local version
        if os.path.exists(LOCAL_VERSION_PATH):
            with open(LOCAL_VERSION_PATH, "r") as f:
                local_version = f.read().strip()
        else:
            local_version = None

        if local_version != remote_version:
            print(f"[INFO] Update available: local={local_version}, remote={remote_version}")
            speak("A new update is available. Updating now.", True)

            # Run git pull
            try:
                subprocess.run(["git", "fetch", "origin", BRANCH], check=True)
                subprocess.run(["git", "reset", "--hard", f"origin/{BRANCH}"], check=True)
                speak("Update complete. Please restart me.", True)
                exit(0)
            except subprocess.CalledProcessError as e:
                print(f"[ERROR] Failed to update: {e}")
                speak("I tried to update, but something went wrong.", True)
        else:
            print("[INFO] Already up to date.")
    except Exception as e:
        print(f"[WARN] Could not check updates: {e}")


def load_ssh_log():
    try:
        with open(SSH_LOG_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_ssh_log(log):
    with open(SSH_LOG_FILE, "w") as f:
        json.dump(log, f, indent=4)

def get_current_ssh_users():
    """
    Returns a set of currently connected SSH usernames.
    """
    try:
        result = subprocess.run(["who"], capture_output=True, text=True)
        users = set()
        for line in result.stdout.splitlines():
            if "pts" in line or "ssh" in line:
                users.add(line.split()[0])
        return users
    except Exception as e:
        print(f"[ERROR] Failed to get SSH users: {e}")
        return set()

def monitor_ssh_connections(poll_interval=5):
    """
    Monitor SSH connections and announce connect/disconnect events.
    """
    known_users = load_ssh_log()
    known_set = set(known_users.keys())

    while True:
        current_users = get_current_ssh_users()

        # New connections
        new_users = current_users - known_set
        for user in new_users:
            speak(f"SSH user {user} connected.")
            known_users[user] = time.strftime("%Y-%m-%d %H:%M:%S")

        # Disconnections
        disconnected_users = known_set - current_users
        for user in disconnected_users:
            speak(f"SSH user {user} disconnected.")
            known_users.pop(user, None)

        # Save log
        save_ssh_log(known_users)

        known_set = current_users
        time.sleep(poll_interval)

# Start the SSH monitor in a background thread
def start_ssh_monitor():
    thread = threading.Thread(target=monitor_ssh_connections, daemon=True)
    thread.start()