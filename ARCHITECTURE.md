# Recordings Monitor Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     RASPBERRY PI SYSTEM                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Camera Recording Process (External)                      │  │
│  │  - Records video every 5 minutes                          │  │
│  │  - Saves to ~/recordings/DDMMYYYY_HHMMSS.mp4             │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           │                                      │
│                           ▼                                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  ~/recordings/                                            │  │
│  │  ├── 10022026_000311.mp4  (5 min recording)             │  │
│  │  ├── 10022026_000812.mp4  (5 min recording)             │  │
│  │  ├── 10022026_001312.mp4  (5 min recording)             │  │
│  │  ├── ...                                                  │  │
│  │  └── 10022026_165235.mp4  (currently recording...)       │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           │                                      │
│                           ▼                                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Recordings Monitor (Python)                              │  │
│  │  recordings_mqtt_monitor.py                               │  │
│  │                                                            │  │
│  │  [Scan] → [Parse] → [Analyze] → [Detect] → [Publish]    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           │                                      │
└───────────────────────────┼──────────────────────────────────────┘
                            │
                            ▼ MQTT
                ┌───────────────────────┐
                │   MQTT Broker         │
                │   18.100.207.236:1883 │
                │                       │
                │   Topic:              │
                │   storeyes/           │
                │   {board_id}/         │
                │   recordings          │
                └───────────────────────┘
                            │
                            ▼
                ┌───────────────────────┐
                │  Monitoring Dashboard │
                │  (Subscribers)        │
                └───────────────────────┘
```

## Data Flow

### 1. File Discovery Phase

```python
get_video_files(RECORDINGS_DIR)
    │
    ├─→ Scan directory for *.mp4 files
    │
    ├─→ For each file:
    │   ├─→ Parse filename with regex
    │   │   ├─→ Pattern 1: DDMMYYYY_HHMMSS.mp4
    │   │   └─→ Pattern 2: video_HHMMSS.mp4
    │   │
    │   └─→ Extract datetime object
    │
    └─→ Sort by timestamp (oldest first)

Result: List of (datetime, filename, filepath) tuples
```

### 2. Gap Detection Phase

```python
detect_offline_segments(videos)
    │
    ├─→ Exclude latest file (currently recording)
    │
    ├─→ For each consecutive pair:
    │   │
    │   ├─→ Calculate time gap
    │   │
    │   ├─→ Is gap > expected (5 min) + tolerance (1 min)?
    │   │   │
    │   │   ├─→ YES: Offline segment detected!
    │   │   │   │
    │   │   │   ├─→ Start = current_time + 5 min
    │   │   │   ├─→ End = next_time
    │   │   │   └─→ Add to segments dict
    │   │   │
    │   │   └─→ NO: Normal gap, continue
    │   │
    │   └─→ Handle multi-day segments
    │       (split at midnight)
    │
    └─→ Group segments by date

Result: Dict of {date: [segments]}
```

### 3. Status Check Phase

```python
check_camera_status(videos)
    │
    ├─→ Get latest video timestamp
    │
    ├─→ Calculate time since latest
    │
    └─→ Determine status:
        ├─→ < 5 min: RECORDING
        ├─→ < 7 min: FINISHING
        └─→ > 7 min: OFFLINE
```

### 4. Report Generation Phase

```python
generate_report(videos)
    │
    ├─→ Call detect_offline_segments()
    ├─→ Call check_camera_status()
    ├─→ Calculate statistics
    │   ├─→ Total videos
    │   ├─→ Date range
    │   ├─→ Total offline minutes
    │   └─→ Latest file info
    │
    └─→ Build JSON payload

Result: Complete monitoring report
```

### 5. MQTT Publishing Phase

```python
publish_mqtt(payload, topic)
    │
    ├─→ Attempt 1:
    │   ├─→ Connect to MQTT broker
    │   ├─→ Authenticate
    │   ├─→ Publish JSON payload
    │   └─→ Success? → Exit
    │
    ├─→ Failed? Wait 2 seconds
    │
    ├─→ Attempt 2: (repeat)
    │
    ├─→ Failed? Wait 2 seconds
    │
    └─→ Attempt 3: (final attempt)

Result: Success or Failure
```

## Algorithm Details

### Gap Detection Algorithm

```
Input: Sorted list of video timestamps
Output: Dict of offline segments by date

Expected interval: 5 minutes
Tolerance: 1 minute
Threshold: 6 minutes

For each consecutive pair (current, next):
    gap = next - current
    
    if gap > 6 minutes:
        offline_start = current + 5 minutes
        offline_end = next
        
        # Example:
        # current = 08:05
        # next = 08:35
        # gap = 30 minutes (> 6 minutes)
        # offline_start = 08:10
        # offline_end = 08:35
        # Result: Offline from 08:10 to 08:35
```

### Multi-Day Segment Handling

```
If offline segment spans midnight:
    
    Segment: 2026-02-09 23:45 → 2026-02-10 00:30
    
    Split into two:
    
    Date 1 (2026-02-09):
        start: 23h45
        end: 23h59
    
    Date 2 (2026-02-10):
        start: 00h00
        end: 00h30
```

### Latest File Exclusion

```
Why exclude latest file?
    
    Scenario:
    - 16:50 → video_165000.mp4 starts recording
    - 16:52 → Monitor runs
    - 16:55 → video_165000.mp4 finishes
    
    At 16:52, the gap between 16:45 and 16:50 is 5 min (normal)
    But video_165000.mp4 is still being written!
    
    If we include it:
    - Monitor sees last video at 16:50
    - Calculates gap from 16:50 to now (16:52) = 2 min
    - False alarm: "Recording stopped!"
    
    By excluding latest:
    - Monitor sees last complete video at 16:45
    - Calculates gap from 16:45 to 16:50 = 5 min (OK)
    - No false alarm
```

## File Naming Patterns

### Pattern 1: Full Timestamp

```
Format: DDMMYYYY_HHMMSS.mp4

Examples:
    10022026_000311.mp4
    └┬─┘└┬─┘└──┬─┘└──┬──┘
     │   │     │      │
     │   │     │      └─ Time: 00:03:11
     │   │     └──────── Year: 2026
     │   └──────────────── Month: 02
     └──────────────────── Day: 10

Parsed as: datetime(2026, 2, 10, 0, 3, 11)
```

### Pattern 2: Time Only

```
Format: video_HHMMSS.mp4

Examples:
    video_000402.mp4
          └──┬──┘
             └─ Time: 00:04:02

Parsed as: datetime(today.year, today.month, today.day, 0, 4, 2)
Uses current date
```

## JSON Payload Structure

```json
{
  "board_id": "1000000012345678",        // From /proc/cpuinfo
  "timestamp": "2026-02-10T16:52:45Z",   // ISO 8601 UTC
  
  "camera_status": "RECORDING",          // Status enum
  
  "offline_segments": {                  // Grouped by date
    "2026-02-09": [
      {
        "start": "08h30",                // 24-hour format
        "end": "09h00"
      }
    ]
  },
  
  "latest_recording": {                  // Info about latest file
    "filename": "10022026_165235.mp4",
    "timestamp": "2026-02-10T16:52:35",
    "size_mb": 8.45
  },
  
  "total_videos": 245,
  "total_offline_segments": 1
}
```

## Edge Cases Handled

### 1. Empty Directory
```
Input: No video files
Output: 
{
  "camera_status": "NO_RECORDINGS",
  "offline_segments": {},
  "total_videos": 0
}
```

### 2. Single Video
```
Input: Only one video file
Output:
{
  "camera_status": "OFFLINE" or "RECORDING" (based on timestamp),
  "offline_segments": {},  // Need at least 2 files to detect gaps
  "total_videos": 1
}
```

### 3. All Videos Recent (No Gaps)
```
Input: Videos at perfect 5-minute intervals
Output:
{
  "camera_status": "RECORDING",
  "offline_segments": {},  // No gaps detected
  "total_videos": N
}
```

### 4. Multiple Gaps Same Day
```
Input:
  08:00, 08:05, 08:10 → GAP → 09:00, 09:05 → GAP → 10:30, 10:35

Output:
{
  "offline_segments": {
    "2026-02-10": [
      {"start": "08h15", "end": "09h00"},
      {"start": "09h10", "end": "10h30"}
    ]
  }
}
```

### 5. Gap Spanning Multiple Days
```
Input:
  Feb 9, 23:50 → GAP → Feb 10, 01:30

Output:
{
  "offline_segments": {
    "2026-02-09": [
      {"start": "23h55", "end": "23h59"}
    ],
    "2026-02-10": [
      {"start": "00h00", "end": "01h30"}
    ]
  }
}
```

## Performance Characteristics

```
File Count: N videos
Time Complexity: O(N log N)
    - O(N) to scan directory
    - O(N log N) to sort by timestamp
    - O(N) to detect gaps
    - O(1) MQTT publish

Space Complexity: O(N)
    - Store list of N tuples
    - Store offline segments (typically << N)

Typical Performance:
    100 videos: < 0.1 seconds
    1000 videos: < 0.5 seconds
    10000 videos: < 2 seconds
```

## Configuration Matrix

| Parameter | Default | Min | Max | Impact |
|-----------|---------|-----|-----|--------|
| EXPECTED_INTERVAL_MINUTES | 5 | 1 | 60 | Detection threshold |
| TOLERANCE_SECONDS | 60 | 0 | 300 | False positive rate |
| RETRIES | 3 | 1 | 10 | Reliability vs speed |
| TIMEOUT | 5 | 1 | 30 | Network wait time |

### Tuning Examples

**Strict Detection** (catch small gaps):
```bash
EXPECTED_INTERVAL_MINUTES=5
TOLERANCE_SECONDS=30
```

**Relaxed Detection** (fewer false positives):
```bash
EXPECTED_INTERVAL_MINUTES=5
TOLERANCE_SECONDS=120
```

**10-minute Recordings**:
```bash
EXPECTED_INTERVAL_MINUTES=10
TOLERANCE_SECONDS=120
```

## Integration Points

### 1. Input
- Source: File system (~/recordings/)
- Format: MP4 video files with timestamped names
- Frequency: Continuous (new file every 5 min)

### 2. Output
- Destination: MQTT broker
- Format: JSON payload
- Frequency: On-demand or scheduled (cron)

### 3. Dependencies
- Python 3.6+
- paho-mqtt library
- /proc/cpuinfo (for board ID)
- File system access

### 4. Related Systems
- Camera recording process (producer)
- MQTT broker (message bus)
- Dashboard/alerts (consumer)
- Other monitors (siblings)

## Error Handling

```
Level 1: File System Errors
    - Directory not found → Report NO_RECORDINGS
    - Permission denied → Exit with error
    - Invalid filename → Skip file

Level 2: Parsing Errors
    - Invalid date → Skip file
    - Malformed name → Skip file
    - Continue with valid files

Level 3: MQTT Errors
    - Connection failed → Retry (up to 3 times)
    - Publish failed → Retry
    - All retries failed → Exit with error code

Level 4: Runtime Errors
    - Unexpected exception → Log and exit
    - Keyboard interrupt → Clean exit
```

## Monitoring the Monitor

To ensure the monitor itself is working:

1. **Check Logs**: Monitor should run every 10 minutes
2. **MQTT Messages**: Verify messages arrive at broker
3. **Board ID**: Ensure it matches device serial
4. **Timestamp**: Should be recent (within 10 min)
5. **Video Count**: Should increase over time

## Security Considerations

1. **MQTT Credentials**: Stored in environment/config
2. **File Access**: Read-only access to recordings
3. **Board ID**: Unique identifier per device
4. **Network**: MQTT traffic not encrypted (consider TLS)
5. **Logs**: May contain system information

## Future Enhancements

Possible improvements:
- [ ] TLS support for MQTT
- [ ] Configurable time format (12h/24h)
- [ ] Email alerts for long outages
- [ ] Web dashboard
- [ ] Historical trends
- [ ] Video file integrity checks
- [ ] Disk space monitoring
- [ ] Compression detection

