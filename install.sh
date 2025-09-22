#!/bin/bash

# Variables
DEST="$HOME/.selene"
SERVICE_NAME="selene.service"
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

# Step 3: Install Python packages (only once)
echo "[*] Installing Python dependencies..."
"$DEST/venv/bin/pip" install --upgrade pip
"$DEST/venv/bin/pip" install pexpect sounddevice yt-dlp asyncio numpy pydub

# Step 4: Create systemd service
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME"

if [ ! -f "$SERVICE_FILE" ]; then
    echo "[*] Creating systemd service..."
    sudo bash -c "cat > $SERVICE_FILE" <<EOL
[Unit]
Description=Selene AI Assistant
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$DEST
ExecStart=/bin/bash -c 'source $DEST/venv/bin/activate && python3 $DEST/main.py >> $LOG_FILE 2>&1'
Restart=on-failure

[Install]
WantedBy=default.target
EOL

    echo "[*] Reloading systemd daemon..."
    sudo systemctl daemon-reload

    echo "[*] Enabling Selene service to start on boot..."
    sudo systemctl enable $SERVICE_NAME
else
    echo "[*] Systemd service already exists"
fi

echo "[*] Installation complete!"
echo "Start Selene: sudo systemctl start $SERVICE_NAME"
echo "Logs will be saved to: $LOG_FILE"
