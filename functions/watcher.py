import json
import time
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from functions.tts import speak

WATCH_LOG_FILE = "data/watched_files.json"

def load_watch_log():
    try:
        with open(WATCH_LOG_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_watch_log(log):
    with open(WATCH_LOG_FILE, "w") as f:
        json.dump(log, f, indent=4)

class WatchHandler(FileSystemEventHandler):
    def __init__(self, log):
        self.log = log

    def on_created(self, event):
        if not event.is_directory:
            msg = f"New file created: {event.src_path}"
        else:
            msg = f"New folder created: {event.src_path}"
        
        print(msg)
        speak(msg)
        self.log.append({
            "path": event.src_path,
            "type": "folder" if event.is_directory else "file",
            "time": time.strftime("%Y-%m-%d %H:%M:%S")
        })
        save_watch_log(self.log)

def start_folder_watch(directory):
    log = load_watch_log()
    event_handler = WatchHandler(log)
    observer = Observer()
    observer.schedule(event_handler, path=directory, recursive=True)
    observer.start()
    print(f"[INFO] Started watching folder: {directory}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

def start_multi_folder_watch(directories):
    """
    Start watching multiple directories in separate threads.
    """
    for directory in directories:
        thread = threading.Thread(target=start_folder_watch, args=(directory,), daemon=True)
        thread.start()
