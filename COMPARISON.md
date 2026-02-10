# Bash vs Python Monitoring Scripts Comparison

## Overview

The Python recordings monitor follows the same architecture and patterns as the existing bash monitoring scripts.

## Side-by-Side Comparison

### 1. Caisse Monitor (Bash) ↔ Recordings Monitor (Python)

| Feature | Bash (`caisse_monitor.sh`) | Python (`recordings_mqtt_monitor.py`) |
|---------|----------------------------|---------------------------------------|
| **Monitors** | Caisse status file | Video recordings directory |
| **Input Source** | `~/caisse_status.txt` | `~/recordings/*.mp4` |
| **Data Read** | Text file content | Directory listing + filename parsing |
| **Processing** | Read status string | Parse timestamps, detect gaps |
| **Output** | JSON with status | JSON with offline segments |
| **MQTT Topic** | `storeyes/{board_id}/caisse` | `storeyes/{board_id}/recordings` |
| **Board ID** | From `/proc/cpuinfo` | From `/proc/cpuinfo` |
| **Retry Logic** | 3 attempts, 2s delay | 3 attempts, 2s delay |

### 2. Alert Processor Monitor (Bash) ↔ Recordings Monitor (Python)

| Feature | Bash (`alert_processor_monitor.sh`) | Python (`recordings_mqtt_monitor.py`) |
|---------|-------------------------------------|---------------------------------------|
| **Monitors** | Alert processor status | Camera recording status |
| **Status File** | `~/alert-processor-status.txt` | N/A (analyzes files directly) |
| **Metrics** | Status, total, processed | Status, offline segments, video count |
| **Status Values** | Numeric status codes | RECORDING/OFFLINE/NO_RECORDINGS |

### 3. Camera Monitor (Bash) ↔ Recordings Monitor (Python)

| Feature | Bash (`camera_monitor.sh`) | Python (`recordings_mqtt_monitor.py`) |
|---------|----------------------------|---------------------------------------|
| **Check Method** | `rpicam-hello` command | File timestamp analysis |
| **Detection** | Camera hardware status | Recording activity |
| **Status** | ON/OFF | RECORDING/FINISHING/OFFLINE/NO_RECORDINGS |
| **Real-time** | Yes (hardware check) | Near real-time (file-based) |

## Shared Architecture

All monitors (bash and Python) share:

### 1. Configuration Pattern
```bash
# Bash
MQTT_HOST="${MQTT_HOST:-18.100.207.236}"
MQTT_PORT="${MQTT_PORT:-1883}"
```

```python
# Python
MQTT_HOST = os.environ.get('MQTT_HOST', '18.100.207.236')
MQTT_PORT = int(os.environ.get('MQTT_PORT', '1883'))
```

### 2. MQTT Publishing
```bash
# Bash
mosquitto_pub \
    -h "$MQTT_HOST" \
    -p "$MQTT_PORT" \
    -u "$MQTT_USER" \
    -P "$MQTT_PASS" \
    -t "$MQTT_TOPIC" \
    -m "$FINAL_PAYLOAD"
```

```python
# Python
client = mqtt.Client()
client.username_pw_set(MQTT_USER, MQTT_PASS)
client.connect(MQTT_HOST, MQTT_PORT, TIMEOUT)
client.publish(topic, json.dumps(payload), qos=QOS, retain=RETAIN)
```

### 3. Retry Logic
```bash
# Bash
attempt=1
while [[ $attempt -le $RETRIES ]]; do
    # ... publish attempt ...
    sleep 2
    ((attempt++))
done
```

```python
# Python
for attempt in range(1, RETRIES + 1):
    # ... publish attempt ...
    time.sleep(2)
```

### 4. Board ID Extraction
```bash
# Bash
BOARD_ID=$(awk '/Serial/ {print $3}' /proc/cpuinfo)
```

```python
# Python
with open('/proc/cpuinfo', 'r') as f:
    for line in f:
        if line.startswith('Serial'):
            return line.strip().split()[-1]
```

### 5. Timestamp Format
```bash
# Bash
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
```

```python
# Python
timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
```

## JSON Payload Structures

### Caisse Monitor
```json
{
  "board_id": "1000000012345678",
  "timestamp": "2026-02-10T16:30:00Z",
  "caisse-status": "ONLINE"
}
```

### Alert Processor Monitor
```json
{
  "board_id": "1000000012345678",
  "timestamp": "2026-02-10T16:30:00Z",
  "alert-processor": {
    "status": "1",
    "total": "150",
    "processed": "145"
  }
}
```

### Camera Monitor
```json
{
  "board_id": "1000000012345678",
  "timestamp": "2026-02-10T16:30:00Z",
  "camera": "ON"
}
```

### Recordings Monitor (Python)
```json
{
  "board_id": "1000000012345678",
  "timestamp": "2026-02-10T16:30:00Z",
  "camera_status": "RECORDING",
  "offline_segments": {
    "2026-02-09": [
      {"start": "08h30", "end": "09h00"}
    ]
  },
  "latest_recording": {
    "filename": "10022026_163000.mp4",
    "timestamp": "2026-02-10T16:30:00",
    "size_mb": 8.45
  },
  "total_videos": 245,
  "total_offline_segments": 1
}
```

## Advantages of Python Version

### For Recordings Monitoring

| Aspect | Bash | Python |
|--------|------|--------|
| **File Parsing** | Complex regex in bash | Native datetime/regex libraries |
| **Data Structures** | Arrays, strings | Lists, dicts, classes |
| **Time Calculations** | `date` command hacks | Native timedelta |
| **JSON Generation** | `jq` or string concat | Native json module |
| **Error Handling** | Limited | Try/except, proper types |
| **Testing** | Difficult | Easy (test_monitor.py) |
| **Maintainability** | Scripts can get messy | Structured, documented |

## When to Use Which

### Use Bash When:
- ✅ Simple status checks (file exists, command output)
- ✅ Direct hardware interaction (rpicam-hello)
- ✅ Quick system commands
- ✅ Minimal dependencies preferred

### Use Python When:
- ✅ Complex data parsing (timestamps, filenames)
- ✅ Date/time calculations
- ✅ Statistical analysis
- ✅ Complex logic with many edge cases
- ✅ Need structured testing
- ✅ Maintainability is important

## Deployment Together

Both bash and Python monitors work harmoniously:

```bash
# /etc/crontab or crontab -e

# Bash monitors - every 5 minutes
*/5 * * * * pi /home/pi/pi-monitoring/caisse_monitor.sh
*/5 * * * * pi /home/pi/pi-monitoring/camera_monitor.sh
*/5 * * * * pi /home/pi/pi-monitoring/alert_processor_monitor.sh

# Python monitor - every 10 minutes
*/10 * * * * pi /home/pi/pi-monitoring-py/recordings_mqtt_monitor.py
```

All publish to same MQTT broker:
- Topic pattern: `storeyes/{board_id}/{component}`
- Same authentication
- Same JSON timestamp format
- Same retry logic

## Migration Path

If you want to migrate bash scripts to Python:

1. ✅ **Recordings Monitor**: Already done! (complex parsing logic)
2. 🤔 **Camera Monitor**: Could migrate (rpicam-hello via subprocess)
3. 🤔 **Caisse Monitor**: Could migrate (simple file read)
4. 🤔 **Alert Processor**: Could migrate (simple file read)

But bash versions work fine for simple cases, so no urgent need to migrate.

## Conclusion

- **Bash scripts**: Great for simple status checks
- **Python script**: Perfect for complex analysis (recordings)
- **Together**: Comprehensive monitoring solution
- **Compatible**: Same infrastructure, same MQTT topics, same patterns

Choose the right tool for each monitoring task! 🚀

