# Quick Start Guide

## Installation

```bash
cd pi-monitoring-py
./install.sh
```

## Test the Monitor

Run the test script to see the monitor in action with sample data:

```bash
./test_monitor.py
```

This will:
1. Create temporary test video files
2. Simulate gaps in recording
3. Run the monitor and display results
4. Clean up test files

## Monitor Your Recordings

### Option 1: Console Output (for testing/debugging)

```bash
./recordings_monitor.py
```

Output example:
```
📹 Recording Monitor Started
📂 Monitoring directory: /home/pi/recordings
🔍 Looking for gaps larger than 5 minutes (±60s tolerance)

✅ Found 245 video files
📅 Date range: 2026-02-09 to 2026-02-10

============================================================
MONITORING REPORT
============================================================
{
  "board_id": "1000000012345678",
  "timestamp": "2026-02-10T16:52:45Z",
  "offline_segments": {
    "2026-02-09": [
      {"start": "08h30", "end": "09h00"},
      {"start": "17h00", "end": "18h15"}
    ]
  },
  ...
}
============================================================

⚠️ OFFLINE SEGMENTS DETECTED:

  📅 2026-02-09:
    • 08h30 → 09h00
    • 17h00 → 18h15

📊 Camera Status: RECORDING
   Camera is currently recording
```

### Option 2: MQTT Publishing (for production)

```bash
./recordings_mqtt_monitor.py
```

This will publish the report to MQTT topic: `storeyes/{board_id}/recordings`

## Custom Configuration

### Monitor Different Directory

```bash
RECORDINGS_DIR=/path/to/videos ./recordings_monitor.py
```

### Change Expected Interval

If your recordings are every 10 minutes instead of 5:

```bash
EXPECTED_INTERVAL_MINUTES=10 ./recordings_monitor.py
```

### Custom MQTT Broker

```bash
MQTT_HOST=192.168.1.100 \
MQTT_PORT=1883 \
MQTT_USER=myuser \
MQTT_PASS=mypass \
./recordings_mqtt_monitor.py
```

## Schedule with Cron

Run every 10 minutes:

```bash
# Edit crontab
crontab -e

# Add this line:
*/10 * * * * /home/pi/pi-monitoring-py/recordings_mqtt_monitor.py >> /home/pi/logs/recordings.log 2>&1
```

Run once per hour:

```bash
0 * * * * /home/pi/pi-monitoring-py/recordings_mqtt_monitor.py >> /home/pi/logs/recordings.log 2>&1
```

## Understanding the Output

### Offline Segments Format

The JSON output groups offline segments by date:

```json
{
  "offline_segments": {
    "2026-02-09": [
      {"start": "08h30", "end": "09h00"}
    ]
  }
}
```

This means:
- On February 9, 2026
- Recording was offline from 08:30 to 09:00

### Camera Status

- `RECORDING`: Currently recording (latest file is recent)
- `FINISHING`: Last recording just finished
- `OFFLINE`: No recording for extended period
- `NO_RECORDINGS`: No video files found

## Troubleshooting

### "No video files found"

Check your recordings directory:
```bash
ls -lh ~/recordings/*.mp4 | head
```

Make sure filenames match the expected format: `DDMMYYYY_HHMMSS.mp4`

### MQTT Connection Issues

Test MQTT connection manually:
```bash
mosquitto_pub -h 18.100.207.236 -u storeyes -P 12345 -t test -m "hello"
```

### See All Configuration Options

```bash
cat README.md | grep -A 20 "Configuration"
```

## Integration Example

Combine with existing monitors in a single cron schedule:

```bash
# Monitor caisse status every 5 minutes
*/5 * * * * /home/pi/pi-monitoring/caisse_monitor.sh

# Monitor camera every 5 minutes  
*/5 * * * * /home/pi/pi-monitoring/camera_monitor.sh

# Monitor alert processor every 5 minutes
*/5 * * * * /home/pi/pi-monitoring/alert_processor_monitor.sh

# Monitor recordings every 10 minutes
*/10 * * * * /home/pi/pi-monitoring-py/recordings_mqtt_monitor.py
```

All monitors publish to the same MQTT broker under different topics:
- `storeyes/{board_id}/caisse`
- `storeyes/{board_id}/camera`
- `storeyes/{board_id}/alert-processor`
- `storeyes/{board_id}/recordings` ← New!

