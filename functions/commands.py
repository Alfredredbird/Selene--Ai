import os
from datetime import datetime

import subprocess

import re
import json
import pexpect
from functions.recorder import clip_last_30_seconds
from functions.tts import speak
import multiprocessing
import threading
import random
import time
import sounddevice as sd
import soundfile as sf
from yt_dlp import YoutubeDL
from functions.functions import *
from functions.recorder import *


music_process = None
current_genre = None
current_song = None
alarm_process = None

#  available commands
COMMANDS_LIST = [
    "what is the time / what time is it - Tells you the current time",
    "hello - Greets you",
    "who am i - Tells you your name if remembered",
    "who are you / intro - Introduces the assistant",
    "search wikipedia <topic> - Searches Wikipedia for a topic",
    "stop - Stops music or alarm",
    "songs list / song list / music list - Lists available songs",
    "play <song or genre> - Plays a specific song or genre",
    "skip - Skips to another song in the same genre",
    "volume <0-100> - Sets the system volume",
    "is <server> up / how is <server> - Checks if a server is online",
    "where do you live - Returns the assistant's IP address",
    "shutdown / shut down - Exits the assistant",
    "leave a note / record a note - Records a 10-second audio note",
    "read my notes - Plays your last saved note",
    "scan - Scans for nearby Bluetooth devices",
    "connect <number> - Connects to a Bluetooth device",
    "unpair <number> - Unpairs a Bluetooth device",
    "set an alarm for <time> - Sets an alarm",
    "timer <minutes> - Sets a timer",
    "spell <word> - Spells a word",
    "download song / get song <name> - Downloads a song from YouTube",
    "play trivia / trivia game - Starts a trivia game",
    "black - Plays a special music track"
]



def handle_command(command, NAME,speaker_name):
    global music_process
    global current_genre, current_song


    command = command.lower()

    
    if "clip that" in command:
        try:
            clip_last_30_seconds() 
            if speaker_name:
                return f"{speaker_name}, the last 30 seconds have been clipped and saved."
            else:
                return "The last 30 seconds have been clipped and saved."
        except Exception as e:
            return f"Failed to clip audio: {str(e)}"


    if "what is the time" in command or "what time is it" in command:
        if speaker_name == None:
            return "It is " + datetime.now().strftime("%H:%M")
        else:
         return f"{speaker_name}" + f" The time is " + datetime.now().strftime("%H:%M")
    
    if "shutdown computer" in command or "shut down computer" in command:
         os.system("shutdown now")

    elif "hello" in command:
        if speaker_name == None:
         return "Hi there! How can I help?"
        else:
         return f"Hello {speaker_name}! How can I help?"
    
    elif "bye" in command or "exit" in command or "quit" in command or "goodbye" in command:
        if speaker_name == None:
         return "Goodbye?"
        else:
         return f"Goodbye {speaker_name}!"
        
    elif "help" in command:
        help_text = "Here are the commands you can use:\n"
        for cmd in COMMANDS_LIST:
            help_text += f"• {cmd}\n"
        return help_text

    elif "who am i" in command:
        if speaker_name == None:
         return "I do not know you buy your name. ask me to remeber you as followed by your name and i will remeber you."
        else:
         return f"your name is {speaker_name}!"

    elif any(kw in command for kw in ["who are you", "who is you", "intro", "tell me about yourself"]):
        return f"Hi there! My name is {NAME}, your virtual assistant! I am running on Ubuntu!"
    
    elif "search wikipedia" in command:
        # Extract search term after "search wikipedia"
        parts = command.split("search wikipedia", 1)
        if len(parts) > 1:
            search_term = parts[1].strip()
            if search_term:
                return searchWikipedia(search_term)
            else:
                return "Please provide a topic to search on Wikipedia."

    elif command.strip() == "stop":
     global alarm_process
     if alarm_process and alarm_process.poll() is None:
        alarm_process.terminate()
        alarm_process = None
        return "Alarm stopped."
     elif music_process and music_process.poll() is None:
        music_process.terminate()
        music_process = None
        return "Stopping the music."
     else:
        return "Nothing is playing right now."


    elif any(kw in command for kw in ["songs list", "song list", "music list"]):
        songs = getFiles("data/music")
        return f"I found {', '.join(songs)} in your library"

    elif any(kw in command for kw in ["open home", "open downloads", "open documents",
                                  "open pictures", "open videos", "open public",
                                  "open templates", "open snap", "open desktop"]):
        return open_directory(command)

    elif command.startswith("open "):
        app_name = command.replace("open", "", 1).strip()
        if not app_name:
            return "Please say the name of the application you want to open."
        return open_application(app_name)

    elif command.startswith("close "):
        app_name = command.replace("close", "", 1).strip()
        if not app_name:
            return "Please say the name of the application you want to close."
        return close_application(app_name, force=False)

    elif command.startswith("force close ") or command.startswith("close -9 "):
        app_name = command.replace("force close", "", 1).replace("close -9", "", 1).strip()
        if not app_name:
            return "Please say the name of the application you want to force close."
        return close_application(app_name, force=True)

    elif "play" in command:
     command = command.replace("music", "")
     parts = command.split("play", 1)
     if len(parts) > 1:
        request = parts[1].strip().lower()

        metadata_path = "config/songs_metadata.json"
        if not os.path.exists(metadata_path):
            return "Music metadata not found."

        with open(metadata_path, "r") as f:
            music_metadata = json.load(f)

        requested_filename = f"{request}.mp3"
        filepath = os.path.join("data/music", requested_filename)
        if os.path.exists(filepath):
            if music_process and music_process.poll() is None:
                music_process.terminate()

            music_process = subprocess.Popen(["mpg123", filepath])
            current_song = requested_filename
            current_genre = next((track["genre"].lower() for track in music_metadata if track["filename"].lower() == requested_filename), None)
            return f"Playing {request}"

        matching_tracks = [
            track for track in music_metadata
            if request in track.get("genre", "").lower()
        ]
        if matching_tracks:
            selected_track = matching_tracks[0]
            filepath = os.path.join("data/music", selected_track["filename"])
            if os.path.exists(filepath):
                if music_process and music_process.poll() is None:
                    music_process.terminate()

                music_process = subprocess.Popen(["mpg123", filepath])
                current_song = selected_track["filename"]
                current_genre = selected_track["genre"].lower()
                return f"Playing {selected_track['filename'][:-4]} from genre '{current_genre}'"
            
        if speaker_name == None:
         return f"Sorry, I couldn't find a song or genre matching '{request}'."
        else:
         return f"Sorry {speaker_name}, I couldn't find a song or genre matching '{request}'."
        
    elif "skip" in command:
      if not current_genre:
        return "No genre is currently being played to skip within."

      metadata_path = "config/songs_metadata.json"
      if not os.path.exists(metadata_path):
        return "Music metadata not found."

      with open(metadata_path, "r") as f:
        music_metadata = json.load(f)

      matching_tracks = [
        track for track in music_metadata
        if track.get("genre", "").lower() == current_genre and track["filename"] != current_song
      ]

      if not matching_tracks:
        return f"No other songs found in the genre '{current_genre}'."

      
      next_track = random.choice(matching_tracks)
      filepath = os.path.join("data/music", next_track["filename"])

      if os.path.exists(filepath):
        if music_process and music_process.poll() is None:
            music_process.terminate()

        music_process = subprocess.Popen(["mpg123", filepath])
        current_song = next_track["filename"]
        return f"Skipped! Now playing {next_track['filename'][:-4]} from genre '{current_genre}'"
      else:
        return f"Could not find the file {next_track['filename']} on disk."


    elif "volume" in command:
        match = re.search(r"volume\s+(\d{1,3})", command)
        if match:
            volume = int(match.group(1))
            if 0 <= volume <= 100:
                subprocess.run(["amixer", "sset", "Master", f"{volume}%"])
                if speaker_name == None:
                 return f"Volume set to {volume} percent."
                else:
                   return f"{speaker_name}, I set the volume to {volume} percent."
            else:
                return "Volume must be between 0 and 100."
            
    elif "is" in command and "up" in command:
     parts = command.split("is", 1)
     if len(parts) > 1:
        server_name = parts[1].replace("up", "").strip().lower()
        return check_server_status(server_name)

    elif "how is" in command:
        parts = command.split("how is", 1)
        if len(parts) > 1:
            server_name = parts[1].strip().lower()
            return check_server_status(server_name)

    elif "where do you live" in command:
        return f"I live at {get_local_ip()}"


    
    elif "leave a note" in command or "record a note" in command:
        os.makedirs("data/notes", exist_ok=True)
        os.makedirs("config", exist_ok=True)
        
        timestamp = datetime.now().strftime("%m-%d_%H-%M")
        filename = f"note_{timestamp}.wav"
        filepath = os.path.join("data/notes", filename)

        speak("Recording your note for 10 seconds.", True)

        try:
            # Record audio
            duration = 10  # seconds
            samplerate = 44100
            recording = sd.rec(int(samplerate * duration), samplerate=samplerate, channels=1)
            sd.wait()
            sf.write(filepath, recording, samplerate)

            # Save note metadata
            notes_json = "config/notes.json"
            notes = []
            if os.path.exists(notes_json):
                with open(notes_json, "r") as f:
                    notes = json.load(f)

            notes.append({"filename": filename, "timestamp": timestamp})
            with open(notes_json, "w") as f:
                json.dump(notes, f, indent=2)

            return "Note saved successfully."
        except Exception as e:
            return f"Failed to record note: {str(e)}"

    elif "read my notes" in command:
        notes_json = "config/notes.json"
        if not os.path.exists(notes_json):
            return "You have no saved notes yet."

        with open(notes_json, "r") as f:
            notes = json.load(f)

        if not notes:
            return "You have no notes to read."

        last_note = notes[-1]
        filepath = os.path.join("data/notes", last_note["filename"])
        if os.path.exists(filepath):
            path = "data/notes/" + last_note["filename"]
            speak(f"Playing your last note from {last_note['timestamp']}.", True)
            subprocess.Popen(["aplay", path])
            time.sleep(11)
            return "and thats it!"
        else:
            return "The audio file for your last note was not found."


    elif command.strip() == "scan":

        try:
            child = pexpect.spawn("bluetoothctl", timeout=10)
            child.expect("#")  # wait for the prompt

            child.sendline("power on")
            child.expect("#")

            child.sendline("scan on")
            found_devices = {}

            start_time = datetime.now()
            while (datetime.now() - start_time).seconds < 8:
                try:
                    child.expect("Device ([0-9A-F:]{17}) (.+)", timeout=1)
                    mac, name = child.match.groups()
                    found_devices[mac.decode()] = name.decode()
                except pexpect.exceptions.TIMEOUT:
                    continue  # Keep waiting

            child.sendline("scan off")
            child.expect("#")
            child.sendline("exit")

            # Format and save
            results = [{"mac": mac, "name": name} for mac, name in found_devices.items()]
            os.makedirs("config", exist_ok=True)
            with open("config/ble.json", "w") as f:
                json.dump(results, f, indent=4)

            return f"Discovered {len(results)} nearby Bluetooth devices. Saved to config."

        except Exception as e:
            return f"Bluetooth scan failed: {e}"

    elif "record my voice profile as" in command or "remember me as" in command:
        match = re.search(r"(?:record my voice profile as|remember me as) (\w+)", command)
        if match:
            name = match.group(1)
            try:
                return create_combined_voice_sample(name, NAME)
            except Exception as e:
                return f"Failed to record voice profile: {e}"
        else:
            return "I couldn't understand the name. Please try again."


    elif "set an alarm for" in command:
     match = re.search(r"set an alarm for (\d{1,2})(?::(\d{2}))?\s*(am|pm)?", command)
     if match:
        hour = int(match.group(1))
        minute = int(match.group(2)) if match.group(2) else 0
        am_pm = match.group(3)

        # Convert AM/PM to 24-hour format
        if am_pm:
            am_pm = am_pm.lower()
            if am_pm == "pm" and hour != 12:
                hour += 12
            elif am_pm == "am" and hour == 12:
                hour = 0
        elif hour > 23:
            return "Invalid time. Use 24-hour format or include AM/PM."

        # Set and calculate alarm time
        now = datetime.now()
        alarm_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if alarm_time < now:
            alarm_time += timedelta(days=1)

        seconds_until_alarm = (alarm_time - now).total_seconds()

        def alarm_worker():
            time.sleep(seconds_until_alarm)
            global alarm_process
            alarm_process = subprocess.Popen(["mpg123", "data/alarms/alarm.mp3"])

        threading.Thread(target=alarm_worker, daemon=True).start()

        return f"Alarm set for {hour:02d}:{minute:02d}"
     else:
        return "Sorry, I couldn't understand the time. Try 'set an alarm for 14:30' or '7:15 PM'."


    elif "spell" in command:
        parts = command.split("spell", 1)
        if len(parts) > 1:
            word = parts[1].strip()
            if not word:
                return "Please say a word to spell."

            spelled = '. '.join(char.upper() for char in word if char.isalpha()) + '.'
            return f"{word.capitalize()} is spelled: {spelled}"
        else:
            return "Please say a word to spell."

    elif "download song" in command or "get song" in command:
        parts = command.split("download song", 1)
        if len(parts) == 1:
            parts = command.split("get song", 1)
        if len(parts) > 1:
            song_name = parts[1].strip()
            if not song_name:
                return "Please say the name of the song."

            try:
                
                

                os.makedirs("data/music", exist_ok=True)

                ydl_opts = {
                    'format': 'bestaudio/best',
                    'noplaylist': True,
                    'quiet': True,
                    'outtmpl': 'data/music/%(title)s.%(ext)s',
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                }

                with YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(f"ytsearch1:{song_name}", download=True)
                    title = info['entries'][0]['title']
                return f"Downloaded '{title}' as MP3."
            except Exception as e:
                return f"Failed to download: {e}"
        else:
            return "Please say the name of the song."

    if "play trivia" in command or "trivia game" in command:
     return trivia_game()


    elif command.startswith("connect"):
     word_to_number = {
        "one": 1, "two": 2, "too": 2, "to": 2, "three": 3, "four": 4,
        "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10
     }

     parts = command.split("connect", 1)
     if len(parts) > 1:
        target = parts[1].strip()

        if target.isdigit():
            index = int(target) - 1
        else:
            index = word_to_number.get(target.lower(), None)
            if index is not None:
                index -= 1

        if index is not None:
            try:
                with open("config/ble.json", "r") as f:
                    devices = json.load(f)

                # Create a process to handle connection
                pool = multiprocessing.Pool(processes=1)
                async_result = pool.apply_async(bluetooth_connect_worker, (index, devices))
                return "Attempting to connect to the Bluetooth device in the background..."

            except FileNotFoundError:
                return "No devices found. Please run 'scan' first."

            except Exception as e:
                return f"Bluetooth connection failed: {e}"
        else:
            return "I couldn't understand the device number. Please say something like 'connect one' or 'connect 2'."
        
    elif "timer" in command:
        minutes = parse_minutes_from_command(command)
        if minutes is None:
            return "Sorry, I couldn't understand the timer duration."

       
        def timer_worker(mins):
            time.sleep(mins * 60)
            speak("Your timer is up!", True)
            print(f"\n\n⏰ Reminder: {mins} minute timer is up!\n")

        threading.Thread(target=timer_worker, args=(minutes,), daemon=True).start()

        return f"Okay! I set a timer for {minutes} minute{'s' if minutes > 1 else ''}."

    elif command.startswith("unpair"):

     word_to_number = {
        "one": 1,
        "two": 2, "too": 2, "to": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine": 9,
        "ten": 10
     }

     parts = command.split("unpair", 1)
     if len(parts) > 1:
        target = parts[1].strip()

        if target.isdigit():
            index = int(target) - 1
        else:
            index = word_to_number.get(target.lower(), None)
            if index is not None:
                index -= 1

        if index is not None:
            try:
                with open("config/ble.json", "r") as f:
                    devices = json.load(f)

                if index < 0 or index >= len(devices):
                    return f"Invalid device number. Please choose between 1 and {len(devices)}."

                device = devices[index]
                mac = device["mac"]

                child = pexpect.spawn("bluetoothctl", timeout=10)
                child.expect("#")

                child.sendline("power on")
                child.expect("#")

                child.sendline(f"remove {mac}")
                child.expect(["Device has been removed", "Failed to remove", pexpect.EOF, pexpect.TIMEOUT], timeout=10)

                output = child.before.decode().strip()
                child.sendline("exit")
                child.expect(pexpect.EOF)
                if child.isalive():
                    child.close(force=True)


                if "Device has been removed" in output:
                    return f"Unpaired successfully from device."
                else:
                    # return f"Failed to unpair from {device['name']}. "
                    return f"Failed to unpair from device. "

            except FileNotFoundError:
                return "No devices found. Please run 'scan' first."

            except Exception as e:
                return f"Bluetooth unpairing failed."
        else:
            return "I couldn't understand the device number. Please say something like 'unpair one' or 'unpair 2'."


    return "Sorry, I do not know that command yet."

