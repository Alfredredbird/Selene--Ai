#!/bin/bash

# Variables
DEST="$HOME/.selene"
SERVICE_NAME="selene.service"
SERVICE_FILE="$HOME/.config/systemd/user/$SERVICE_NAME"
LOG_FILE="$DEST/selene.log"

echo "[*] Creating destination directory..."
mkdir -p "$DEST"

# Copy files only if not already present
if [ ! -f "$DEST/main.py" ]; then
    echo "[*] Copying Selene files to $DEST..."
    cp -r ~/Desktop/Selene\ -Ai/* "$DEST"
else
    echo "[*] Selene files already copied"
fi

# Step 1: Install system packages (only if missing)
echo "[*] Installing system packages..."
sudo apt update
for pkg in alsa-utils mpg123 mpv; do
    if ! dpkg -s "$pkg" >/dev/null 2>&1; then
        sudo apt install -y "$pkg"
    else
        echo "[*] $pkg already installed"
    fi
done

# Step 2: Create virtual environment if it doesn't exist
if [ ! -d "$DEST/venv" ]; then
    echo "[*] Creating virtual environment..."
    python3 -m venv "$DEST/venv"
else
    echo "[*] Virtual environment already exists"
fi

# Step 3: Install Python packages
echo "[*] Installing Python dependencies..."
"$DEST/venv/bin/pip" install --upgrade pip
"$DEST/venv/bin/pip" install pexpect sounddevice yt-dlp asyncio numpy pydub

# Step 4: Create user systemd service
mkdir -p "$HOME/.config/systemd/user"

echo "[*] Creating user systemd service..."
cat > "$SERVICE_FILE" <<EOL
[Unit]
Description=Selene AI Assistant
After=network.target sound.target

[Service]
Type=simple
WorkingDirectory=$DEST
ExecStart=$DEST/venv/bin/python3 $DEST/main.py
Restart=on-failure
StandardOutput=append:$LOG_FILE
StandardError=append:$LOG_FILE
Environment="XDG_RUNTIME_DIR=/run/user/$(id -u)"
Environment="PULSE_SERVER=unix:/run/user/$(id -u)/pulse/native"

[Install]
WantedBy=default.target
EOL

# Step 5: Reload and enable service
echo "[*] Reloading user systemd daemon..."
systemctl --user daemon-reload

echo "[*] Enabling Selene service to start on login..."
systemctl --user enable "$SERVICE_NAME"

echo "[*] Installation complete!"
echo "Start Selene: systemctl --user start $SERVICE_NAME"
echo "Check status : systemctl --user status $SERVICE_NAME"
echo "Logs will be saved to: $LOG_FILE"
