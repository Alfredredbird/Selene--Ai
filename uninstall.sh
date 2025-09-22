#!/bin/bash

DEST="$HOME/.selene"
SERVICE_NAME="selene.service"
SERVICE_FILE="$HOME/.config/systemd/user/$SERVICE_NAME"

echo "[*] Stopping Selene service..."
systemctl --user stop "$SERVICE_NAME"

echo "[*] Disabling Selene service..."
systemctl --user disable "$SERVICE_NAME"

echo "[*] Removing user systemd service file..."
rm -f "$SERVICE_FILE"

echo "[*] Reloading user systemd daemon..."
systemctl --user daemon-reload

echo "[*] Removing Selene directory..."
rm -rf "$DEST"

echo "[*] Uninstallation complete!"
