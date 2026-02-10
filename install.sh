#!/usr/bin/env bash
set -euo pipefail

#############################################
# Recordings Monitor Installation Script
#############################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="$(command -v python3)"

echo "🚀 Installing Recordings Monitor..."
echo ""

# Check if Python 3 is installed
if [[ -z "$PYTHON_BIN" ]]; then
    echo "❌ Python 3 is not installed. Please install Python 3 first."
    exit 1
fi

echo "✅ Python 3 found: $("$PYTHON_BIN" --version)"
echo ""

# Install Python MQTT dependency via apt (Debian/Raspberry Pi OS style)
echo "📦 Installing python3-paho-mqtt (system package)..."
sudo apt-get update
sudo apt-get install -y python3-paho-mqtt

# Make scripts executable
echo "🔧 Making scripts executable..."
chmod +x recordings_monitor.py
chmod +x main.py

#############################################
# Configure cron job (every minute)
#############################################

echo "🕒 Configuring cron job to run every minute..."

# Ensure logs directory exists (for stdout/stderr)
mkdir -p "$HOME/logs"

# Build the cron line
CRON_LINE="* * * * * cd $SCRIPT_DIR && $PYTHON_BIN $SCRIPT_DIR/main.py >> \\$HOME/logs/recordings.log 2>&1"

# Read existing crontab (if any), remove any previous entries for this script, then add the new one
EXISTING_CRON="$(crontab -l 2>/dev/null || true)"
FILTERED_CRON="$(printf '%s\n' "$EXISTING_CRON" | grep -v "$SCRIPT_DIR/main.py" || true)"

printf '%s\n%s\n' "$FILTERED_CRON" "$CRON_LINE" | crontab -

echo "✅ Cron job installed:"
echo "    $CRON_LINE"

echo ""
echo "✅ Installation complete!"
echo ""
echo "Usage:"
echo "  Monitor recordings:  ./recordings_monitor.py"
echo "  Publish to MQTT:     ./main.py"
echo "  (Cron: runs main.py every minute for continuous monitoring)"
echo ""
echo "Configuration (environment variables):"
echo "  RECORDINGS_DIR              Directory to monitor (default: ~/recordings)"
echo "  EXPECTED_INTERVAL_MINUTES   Expected interval between videos (default: 5)"
echo "  TOLERANCE_SECONDS           Tolerance for gaps (default: 60)"
echo "  MQTT_HOST                   MQTT broker host (default: 18.100.207.236)"
echo "  MQTT_PORT                   MQTT broker port (default: 1883)"
echo "  MQTT_USER                   MQTT username (default: storeyes)"
echo "  MQTT_PASS                   MQTT password (default: 12345)"
echo "  MQTT_TOPIC                  MQTT topic template (default: storeyes/{board_id}/recordings)"
echo ""
echo "Example:"
echo "  RECORDINGS_DIR=~/videos ./recordings_monitor.py"
echo ""

