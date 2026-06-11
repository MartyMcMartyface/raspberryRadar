#!/bin/bash
# ============================================================
#  raspberryRadar – Installation script for Raspberry Pi OS
#  Run with: bash install.sh
# ============================================================

echo "=== raspberryRadar Installer ==="

# Update package list
sudo apt-get update -y

# Install Python dependencies
echo "Installing Python dependencies..."
sudo apt-get install -y python3-pip python3-pygame

pip3 install requests --break-system-packages

echo ""
echo "=== Installation complete ==="
echo ""
echo "Next steps:"
echo "  1. Set your coordinates in config.py"
echo "  2. Run:  python3 main.py"
echo ""
echo "To enable autostart on boot:"
echo "  bash autostart.sh"
