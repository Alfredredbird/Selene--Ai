import os
import json
import platform
import psutil
from pathlib import Path
from functions.tts import *

SYSTEM_INFO_FILE = Path.home() / ".selene/.selene_system_info.json"

def collect_system_info():
    """Collects system info and compares it to previous info if exists."""
    current_info = {
        "platform": platform.system(),
        "platform_version": platform.version(),
        "platform_release": platform.release(),
        "architecture": platform.machine(),
        "processor": platform.processor(),
        "cpu_count": psutil.cpu_count(logical=True),
        "ram_gb": round(psutil.virtual_memory().total / (1024 ** 3), 2),
        "hostname": platform.node()
    }

    if not SYSTEM_INFO_FILE.exists() or SYSTEM_INFO_FILE.stat().st_size == 0:
        # No previous info saved
        with open(SYSTEM_INFO_FILE, "w") as f:
            json.dump(current_info, f, indent=4)
        speak("Let me learn more about you and your system.", True)
        return True  # allow program to continue

    # Load previous system info
    with open(SYSTEM_INFO_FILE, "r") as f:
        saved_info = json.load(f)

    if saved_info != current_info:
        speak("Looks like your system changed.", True)
        # Optionally update saved info to new system
        with open(SYSTEM_INFO_FILE, "w") as f:
            json.dump(current_info, f, indent=4)
        return False  # stop or handle as needed

    # System info matches, continue
    return True
