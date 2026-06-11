#!/bin/bash
# ============================================================
#  raspberryRadar – Autostart setup
#  Registers a systemd service that launches the radar on boot.
#  Run with: bash autostart.sh
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICE_FILE="/etc/systemd/system/raspberryradar.service"

sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=raspberryRadar Display
After=network.target graphical.target

[Service]
User=$USER
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/$USER/.Xauthority
WorkingDirectory=$SCRIPT_DIR
ExecStart=/usr/bin/python3 $SCRIPT_DIR/main.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=graphical.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable raspberryradar.service

echo "Autostart configured!"
echo "Start:   sudo systemctl start raspberryradar"
echo "Status:  sudo systemctl status raspberryradar"
echo "Stop:    sudo systemctl stop raspberryradar"
