# Recordings Monitor - Project Summary

## 📁 Project Structure

```
pi-monitoring-py/
├── recordings_monitor.py         # Main monitoring script (console output)
├── recordings_mqtt_monitor.py    # MQTT publishing version
├── test_monitor.py               # Test script with sample data
├── requirements.txt              # Python dependencies
├── install.sh                    # Installation script
├── README.md                     # Complete documentation
├── USAGE.md                      # Quick start guide
├── example_output.json           # Example JSON output
├── .gitignore                    # Git ignore rules
└── PROJECT_SUMMARY.md            # This file
```

## 🎯 Purpose

Monitor video recordings directory for gaps/offline segments based on file timestamps and publish status to MQTT broker.

## 📝 Key Features

1. **Automatic Gap Detection**: Analyzes video filenames (format: `DDMMYYYY_HHMMSS.mp4`) to detect recording timestamps
2. **Offline Segment Reporting**: Identifies gaps larger than expected interval (default: 5 minutes)
3. **JSON Output**: Produces structured reports with offline segments grouped by date
4. **MQTT Integration**: Compatible with existing pi-monitoring bash scripts
5. **Configurable**: All parameters via environment variables
6. **Robust**: Handles edge cases (multi-day gaps, active recordings, etc.)

## 📊 Output Format

```json
{
  "2026-02-09": [
    {"start": "08h30", "end": "09h00"},
    {"start": "17h00", "end": "18h15"}
  ],
  "2026-02-10": [
    {"start": "12h00", "end": "12h30"}
  ]
}
```

## 🚀 Quick Start

```bash
# Install
./install.sh

# Test with sample data
./test_monitor.py

# Monitor your recordings
./recordings_monitor.py

# Publish to MQTT
./recordings_mqtt_monitor.py
```

## ⚙️ Configuration

Key environment variables:

- `RECORDINGS_DIR`: Directory to monitor (default: `~/recordings`)
- `EXPECTED_INTERVAL_MINUTES`: Expected interval between videos (default: 5)
- `TOLERANCE_SECONDS`: Gap tolerance (default: 60)
- `MQTT_HOST`: MQTT broker host (default: 18.100.207.236)
- `MQTT_TOPIC`: MQTT topic template (default: `storeyes/{board_id}/recordings`)

## 🔗 Integration with Existing Monitors

This tool follows the same patterns as the bash monitoring scripts:

### Bash Monitors (pi-monitoring/)
- `caisse_monitor.sh` → `storeyes/{board_id}/caisse`
- `camera_monitor.sh` → `storeyes/{board_id}/camera`
- `alert_processor_monitor.sh` → `storeyes/{board_id}/alert-processor`

### Python Monitor (pi-monitoring-py/)
- `recordings_mqtt_monitor.py` → `storeyes/{board_id}/recordings` ✨ NEW

All use:
- Same MQTT broker configuration
- Similar retry logic
- Compatible JSON payload format
- Can be scheduled together via cron

## 📋 Cron Integration Example

```bash
# Existing monitors (every 5 minutes)
*/5 * * * * /home/pi/pi-monitoring/caisse_monitor.sh
*/5 * * * * /home/pi/pi-monitoring/camera_monitor.sh
*/5 * * * * /home/pi/pi-monitoring/alert_processor_monitor.sh

# New recordings monitor (every 10 minutes)
*/10 * * * * /home/pi/pi-monitoring-py/recordings_mqtt_monitor.py
```

## 🧪 Testing

Run the test script to verify functionality:

```bash
./test_monitor.py
```

This creates a temporary directory with 300 test video files spanning ~25 hours with two intentional gaps:
- 30-minute gap around 08:40-09:10
- 1-hour gap around 17:10-18:10

The test demonstrates:
- File parsing
- Gap detection
- Report generation
- Multi-day handling

## 📚 Documentation Files

- **README.md**: Complete technical documentation
- **USAGE.md**: Quick start and common use cases
- **PROJECT_SUMMARY.md**: This overview document
- **example_output.json**: Sample JSON output

## 🛠️ Dependencies

- Python 3.6+
- paho-mqtt (for MQTT publishing)

## 🔍 How It Works

1. Scan recordings directory for `.mp4` files
2. Parse filenames to extract timestamps
3. Sort by timestamp and exclude latest (active) file
4. Compare intervals between consecutive files
5. Identify gaps > expected interval + tolerance
6. Calculate offline segments with start/end times
7. Group by date and generate JSON report
8. Publish to MQTT (if using mqtt version)

## 💡 Example Scenario

**Recordings folder:**
```
10022026_080000.mp4  (08:00)
10022026_080500.mp4  (08:05)  ← 5 min gap (OK)
10022026_083000.mp4  (08:30)  ← 25 min gap (OFFLINE!)
10022026_083500.mp4  (08:35)
```

**Detected offline segment:**
```json
{
  "2026-02-10": [
    {"start": "08h10", "end": "08h30"}
  ]
}
```

## 📞 Support

See README.md for:
- Complete configuration options
- Troubleshooting guide
- Advanced usage examples
- Environment variable reference

## 📄 License

Part of the pi-monitoring-group project.

---

**Created**: February 2026  
**Purpose**: Monitoring video recordings for Raspberry Pi camera systems  
**Language**: Python 3  
**Integration**: Compatible with existing bash monitoring infrastructure

