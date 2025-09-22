#!/bin/bash

DEST="$HOME/.selene"
SERVICE_NAME="selene.service"

echo "[*] Stopping Selene service..."
sudo systemctl stop $SERVICE_NAME

echo "[*] Disabling Selene service..."
sudo systemctl disable $SERVICE_NAME

echo "[*] Removing systemd service file..."
sudo rm -f /etc/systemd/system/$SERVICE_NAME
sudo systemctl daemon-reload

echo "[*] Removing Selene directory..."
rm -rf "$DEST"

echo "[*] Uninstallation complete!"
