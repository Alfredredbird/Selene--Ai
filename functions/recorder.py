import os
import sounddevice as sd
import soundfile as sf
import threading
from datetime import datetime
from collections import deque
import subprocess
import re
# -------------------------
# Configuration
# -------------------------
os.makedirs("data/voice_clips", exist_ok=True)
os.makedirs("data/screen_recordings", exist_ok=True)

SAMPLERATE = 44100
CHANNELS = 1
RECORD_DURATION = 120  # 2 minutes
CLIP_DURATION = 30     # 30 seconds for manual clip

MAX_SAMPLES = RECORD_DURATION * SAMPLERATE
CLIP_SAMPLES = CLIP_DURATION * SAMPLERATE

recording_buffer = deque(maxlen=MAX_SAMPLES)
stop_flag = threading.Event()
recorder_thread = None
screen_process = None
screen_filepath = None

# -------------------------
# Audio utils
# -------------------------
def save_clip(buffer, clip_name=None):
    if clip_name is None:
        clip_name = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filepath = os.path.join("data/voice_clips", f"{clip_name}.wav")
    sf.write(filepath, list(buffer), SAMPLERATE)
    print(f"[INFO] Saved audio clip: {filepath}")
    return filepath

def audio_callback(indata, frames, time, status):
    if status:
        print(status)
    recording_buffer.extend(indata.copy())

# -------------------------
# Recorder thread
# -------------------------
def start_audio_recording():
    global recorder_thread
    if recorder_thread and recorder_thread.is_alive():
        print("[INFO] Audio recorder already running")
        return

    stop_flag.clear()

    def recorder():
        with sd.InputStream(channels=CHANNELS, samplerate=SAMPLERATE, callback=audio_callback):
            print("[INFO] Audio recording started.")
            while not stop_flag.is_set():
                sd.sleep(1000)

    recorder_thread = threading.Thread(target=recorder, daemon=True)
    recorder_thread.start()

# -------------------------
# Screen recording using ffmpeg
# -------------------------
def get_screen_resolution():
    try:
        output = subprocess.check_output("xdpyinfo | grep dimensions", shell=True).decode()
        match = re.search(r"dimensions:\s+(\d+)x(\d+)", output)
        if match:
            return match.group(1), match.group(2)
    except Exception as e:
        print("[WARNING] Could not get screen resolution:", e)
    return "1920", "1080"  # fallback

def start_screen_recording(filename=None):
    global screen_process, screen_filepath

    if filename is None:
        filename = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".mp4"
    screen_filepath = os.path.join("data/screen_recordings", filename)

    display = os.environ.get("DISPLAY")
    if not display:
        raise RuntimeError("No DISPLAY found! Make sure you're running under X11.")

    width, height = get_screen_resolution()

    cmd = [
        "ffmpeg",
        "-y",
        "-video_size", f"{width}x{height}",
        "-framerate", "30",
        "-f", "x11grab",
        "-i", f"{display}+0,0",  # capture top-left of screen
        "-c:v", "libx264",
        "-preset", "ultrafast",
        screen_filepath
    ]

    screen_process = subprocess.Popen(cmd)
    print(f"[INFO] Screen recording started: {screen_filepath}")
    return screen_filepath




def start_recording():
    start_audio_recording()
    start_screen_recording()

# -------------------------
# Stop everything
# -------------------------
def stop_all_recording():
    stop_flag.set()
    if screen_process:
        screen_process.terminate()
        print("[INFO] Screen recording stopped.")
    print("[INFO] Audio recording stopped.")

# -------------------------
# Clip last 30 seconds of audio and combine with video
# -------------------------
def clip_last_30_seconds():
    if len(recording_buffer) < CLIP_SAMPLES:
        buffer_copy = list(recording_buffer)
    else:
        buffer_copy = list(recording_buffer)[-CLIP_SAMPLES:]

    temp_audio_path = save_clip(buffer_copy)

    if screen_process:
        # Stop screen recording briefly
        screen_process.terminate()
        screen_process.wait()  # ensure file is finalized

        clip_name = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + "_clip.mp4"
        clip_output = os.path.join("data/screen_recordings", clip_name)
        
        # Combine audio with finalized video
        ffmpeg_cmd = [
            "ffmpeg",
            "-y",
            "-sseof", f"-{CLIP_DURATION}",
            "-i", screen_filepath,
            "-i", temp_audio_path,
            "-c:v", "copy",
            "-c:a", "aac",
            clip_output
        ]
        subprocess.run(ffmpeg_cmd)
        print(f"[INFO] Saved combined 30-second clip: {clip_output}")

        # Restart screen recording
        start_screen_recording()
    else:
        print("[WARNING] No screen recording found to combine with audio.")
