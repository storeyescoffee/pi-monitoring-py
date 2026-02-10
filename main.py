#!/usr/bin/env python3
"""
Recordings MQTT Monitor - Publishes recording status and offline segments to MQTT
Similar to the bash monitoring scripts but for video recordings
"""

import os
import json
import sys
import time
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from collections import defaultdict

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("❌ paho-mqtt not installed. Install with: pip install paho-mqtt", file=sys.stderr)
    sys.exit(1)


# CONFIG (override via environment variables)
RECORDINGS_DIR = os.path.expanduser(os.environ.get('RECORDINGS_DIR', '~/recordings'))
EXPECTED_INTERVAL_MINUTES = int(os.environ.get('EXPECTED_INTERVAL_MINUTES', '5'))
TOLERANCE_SECONDS = int(os.environ.get('TOLERANCE_SECONDS', '60'))

# MQTT Config
MQTT_HOST = os.environ.get('MQTT_HOST', '18.100.207.236')
MQTT_PORT = int(os.environ.get('MQTT_PORT', '1883'))
MQTT_USER = os.environ.get('MQTT_USER', 'storeyes')
MQTT_PASS = os.environ.get('MQTT_PASS', '12345')
MQTT_TOPIC_TEMPLATE = os.environ.get('MQTT_TOPIC', 'storeyes/{board_id}/recordings')
QOS = int(os.environ.get('QOS', '1'))
RETAIN = os.environ.get('RETAIN', 'true').lower() == 'true'
TIMEOUT = int(os.environ.get('TIMEOUT', '5'))
RETRIES = int(os.environ.get('RETRIES', '3'))

BOARD_ID = None


def get_board_id() -> str:
    """Extract Raspberry Pi board ID from /proc/cpuinfo"""
    try:
        with open('/proc/cpuinfo', 'r') as f:
            for line in f:
                if line.startswith('Serial'):
                    return line.strip().split()[-1]
    except Exception as e:
        print(f"⚠️ Could not read board ID: {e}", file=sys.stderr)
    return "unknown"


def parse_filename(filename: str) -> Optional[Tuple[datetime, str]]:
    """
    Parse video filename and extract timestamp
    Format: DDMMYYYY_HHMMSS.mp4
    Example: 10022026_000311.mp4 -> 2026-02-10 00:03:11
    """
    import re
    
    # Pattern 1: DDMMYYYY_HHMMSS.mp4
    match = re.match(r'(\d{2})(\d{2})(\d{4})_(\d{2})(\d{2})(\d{2})\.mp4$', filename)
    if match:
        day, month, year, hour, minute, second = match.groups()
        try:
            dt = datetime(int(year), int(month), int(day), 
                         int(hour), int(minute), int(second))
            return (dt, filename)
        except ValueError:
            return None
    
    # Pattern 2: video_HHMMSS.mp4 (assume current date)
    match = re.match(r'video_(\d{2})(\d{2})(\d{2})\.mp4$', filename)
    if match:
        hour, minute, second = match.groups()
        try:
            now = datetime.now()
            dt = datetime(now.year, now.month, now.day,
                         int(hour), int(minute), int(second))
            return (dt, filename)
        except ValueError:
            return None
    
    return None


def get_video_files(directory: str) -> List[Tuple[datetime, str, Path]]:
    """Get all video files with their timestamps, sorted by time"""
    videos = []
    
    try:
        recordings_path = Path(directory)
        if not recordings_path.exists():
            return []
        
        for file_path in recordings_path.glob('*.mp4'):
            result = parse_filename(file_path.name)
            if result:
                dt, filename = result
                videos.append((dt, filename, file_path))
    
    except Exception:
        return []
    
    videos.sort(key=lambda x: x[0])
    return videos


def detect_offline_segments(videos: List[Tuple[datetime, str, Path]], 
                           interval_minutes: int = 5,
                           tolerance_seconds: int = 60) -> Dict[str, List[Dict]]:
    """Detect gaps in video recordings (offline segments)"""
    if len(videos) < 2:
        return {}
    
    # Exclude the latest file (currently being written)
    videos_to_check = videos[:-1]
    
    offline_segments = defaultdict(list)
    expected_gap = timedelta(minutes=interval_minutes)
    tolerance = timedelta(seconds=tolerance_seconds)
    
    for i in range(len(videos_to_check) - 1):
        current_time = videos_to_check[i][0]
        next_time = videos_to_check[i + 1][0]
        
        actual_gap = next_time - current_time
        
        if actual_gap > expected_gap + tolerance:
            offline_start = current_time + expected_gap
            offline_end = next_time
            
            date_key = offline_start.strftime('%Y-%m-%d')
            start_str = offline_start.strftime('%Hh%M')
            end_str = offline_end.strftime('%Hh%M')
            
            # Handle segments that span multiple days
            if offline_start.date() != offline_end.date():
                offline_segments[date_key].append({
                    'start': start_str,
                    'end': '23h59'
                })
                
                end_date_key = offline_end.strftime('%Y-%m-%d')
                offline_segments[end_date_key].append({
                    'start': '00h00',
                    'end': end_str
                })
            else:
                offline_segments[date_key].append({
                    'start': start_str,
                    'end': end_str
                })
    
    return dict(offline_segments)


def check_camera_status(videos: List[Tuple[datetime, str, Path]], 
                       interval_minutes: int = 5) -> str:
    """Check if camera is currently recording using lsof command"""
    # Check if any process is writing to recordings directory
    try:
        # Run lsof to check for open files in recordings directory
        lsof_output = subprocess.run(
            ['lsof', '+D', RECORDINGS_DIR],
            capture_output=True,
            text=True,
            timeout=2
        )
        
        if lsof_output.returncode == 0 and lsof_output.stdout.strip():
            # Parse lsof output: COMMAND PID USER FD TYPE DEVICE SIZE/OFF NODE NAME
            # Example: ffmpeg  703 m0hcine24 4w   REG  179,2 54001712 428735 recordings/video_000428.mp4
            for line in lsof_output.stdout.split('\n'):
                if '.mp4' in line:
                    parts = line.split()
                    if len(parts) >= 4:
                        fd = parts[3]  # FD column (e.g., "4w" means file descriptor 4, write mode)
                        if 'w' in fd:  # Check if file is open for writing
                            # Process is writing to an mp4 file = actively recording
                            return 'RECORDING'  # ONLINE
        
        # No active recording process found
        if not videos:
            return 'NO_RECORDINGS'  # OFFLINE
        
        # Fallback: check latest file timestamp if no process found
        latest_dt, _, _ = videos[-1]
        now = datetime.now()
        time_since_latest = now - latest_dt
        expected_interval = timedelta(minutes=interval_minutes)
        
        if time_since_latest < expected_interval + timedelta(minutes=2):
            return 'FINISHING'  # Recently finished
        else:
            return 'OFFLINE'  # OFFLINE
            
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
        # If lsof command fails, fallback to file timestamp check
        if not videos:
            return 'NO_RECORDINGS'
        
        latest_dt, _, _ = videos[-1]
        now = datetime.now()
        time_since_latest = now - latest_dt
        expected_interval = timedelta(minutes=interval_minutes)
        
        if time_since_latest < expected_interval:
            return 'RECORDING'
        elif time_since_latest < expected_interval + timedelta(minutes=2):
            return 'FINISHING'
        else:
            return 'OFFLINE'


def build_payload(videos: List[Tuple[datetime, str, Path]]) -> Dict:
    """Build JSON payload for MQTT"""
    offline_segments = detect_offline_segments(videos, EXPECTED_INTERVAL_MINUTES, TOLERANCE_SECONDS)
    camera_status = check_camera_status(videos, EXPECTED_INTERVAL_MINUTES)
    
    # Calculate statistics
    if videos:
        latest_dt, latest_filename, latest_path = videos[-1]
        try:
            file_size_mb = latest_path.stat().st_size / (1024 * 1024)
        except Exception:
            file_size_mb = 0
    else:
        latest_dt = None
        latest_filename = None
        file_size_mb = 0
    
    payload = {
        'board_id': BOARD_ID,
        'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'camera_status': camera_status,
        'offline_segments': offline_segments,
        'latest_recording': {
            'filename': latest_filename,
            'timestamp': latest_dt.isoformat() if latest_dt else None,
            'size_mb': round(file_size_mb, 2)
        },
        'total_videos': len(videos),
        'total_offline_segments': sum(len(segs) for segs in offline_segments.values())
    }
    
    return payload


def publish_mqtt(payload: Dict, topic: str) -> bool:
    """Publish payload to MQTT with retry logic"""
    
    for attempt in range(1, RETRIES + 1):
        print(f"📡 Publishing recordings status (attempt {attempt}/{RETRIES})")
        
        try:
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
            client.username_pw_set(MQTT_USER, MQTT_PASS)
            
            # Set timeout
            client.connect(MQTT_HOST, MQTT_PORT, TIMEOUT)
            
            # Publish
            result = client.publish(
                topic,
                json.dumps(payload),
                qos=QOS,
                retain=RETAIN
            )
            
            # Wait for publish to complete
            result.wait_for_publish(timeout=TIMEOUT)
            
            client.disconnect()
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print("✅ Recordings status sent")
                return True
            else:
                print(f"⚠️ Publish failed with code: {result.rc}")
        
        except Exception as e:
            print(f"⚠️ Publish failed: {e}")
        
        if attempt < RETRIES:
            print("⚠️ Retrying...")
            time.sleep(2)
    
    print(f"❌ Failed after {RETRIES} attempts")
    return False


def main():
    """Main monitoring function"""
    global BOARD_ID
    BOARD_ID = get_board_id()
    
    # Build MQTT topic
    mqtt_topic = MQTT_TOPIC_TEMPLATE.format(board_id=BOARD_ID)
    
    # Get video files
    videos = get_video_files(RECORDINGS_DIR)
    
    if not videos:
        print("ℹ️ No video files found. Skipping...")
        # Still publish status
        payload = {
            'board_id': BOARD_ID,
            'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'camera_status': 'NO_RECORDINGS',
            'offline_segments': {},
            'total_videos': 0,
            'total_offline_segments': 0
        }
    else:
        # Build payload
        payload = build_payload(videos)
    
    # Publish to MQTT
    success = publish_mqtt(payload, mqtt_topic)
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())


