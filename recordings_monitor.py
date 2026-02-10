#!/usr/bin/env python3
"""
Recordings Monitor - Detects offline segments in video recordings folder
Monitors $HOME/recordings for gaps in video files (5-minute intervals expected)
"""

import os
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from collections import defaultdict


# CONFIG (can be overridden via environment variables)
RECORDINGS_DIR = os.path.expanduser(os.environ.get('RECORDINGS_DIR', '~/recordings'))
EXPECTED_INTERVAL_MINUTES = int(os.environ.get('EXPECTED_INTERVAL_MINUTES', '5'))
TOLERANCE_SECONDS = int(os.environ.get('TOLERANCE_SECONDS', '60'))  # 1 minute tolerance
BOARD_ID = None  # Will be read from /proc/cpuinfo


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
    
    Also handles: video_HHMMSS.mp4 (uses current date)
    
    Returns: (datetime object, original_filename) or None if invalid
    """
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
    """
    Get all video files with their timestamps, sorted by time
    Returns: List of (datetime, filename, filepath) tuples
    """
    videos = []
    
    try:
        recordings_path = Path(directory)
        if not recordings_path.exists():
            print(f"❌ Recordings directory not found: {directory}", file=sys.stderr)
            return []
        
        for file_path in recordings_path.glob('*.mp4'):
            result = parse_filename(file_path.name)
            if result:
                dt, filename = result
                videos.append((dt, filename, file_path))
    
    except Exception as e:
        print(f"❌ Error reading recordings directory: {e}", file=sys.stderr)
        return []
    
    # Sort by timestamp
    videos.sort(key=lambda x: x[0])
    return videos


def detect_offline_segments(videos: List[Tuple[datetime, str, Path]], 
                           interval_minutes: int = 5,
                           tolerance_seconds: int = 60) -> Dict[str, List[Dict]]:
    """
    Detect gaps in video recordings (offline segments)
    
    Args:
        videos: List of (datetime, filename, filepath) tuples
        interval_minutes: Expected interval between videos in minutes
        tolerance_seconds: Tolerance for considering a gap as offline
    
    Returns:
        Dictionary with dates as keys and list of offline segments
        Format: {"2026-02-09": [{"start": "08h30", "end": "09h00"}, ...]}
    """
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
        
        # If gap is larger than expected + tolerance, we have an offline segment
        if actual_gap > expected_gap + tolerance:
            # Offline segment starts at current_time + expected_interval
            # and ends at next_time
            offline_start = current_time + expected_gap
            offline_end = next_time
            
            # Get the date for grouping (use start date)
            date_key = offline_start.strftime('%Y-%m-%d')
            
            # Format times
            start_str = offline_start.strftime('%Hh%M')
            end_str = offline_end.strftime('%Hh%M')
            
            # Handle segments that span multiple days
            if offline_start.date() != offline_end.date():
                # Add segment for start date (until midnight)
                offline_segments[date_key].append({
                    'start': start_str,
                    'end': '23h59'
                })
                
                # Add segment for end date (from midnight)
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


def check_latest_file_status(videos: List[Tuple[datetime, str, Path]], 
                             interval_minutes: int = 5) -> Dict:
    """
    Check if the latest file is being actively written
    Returns status information about the latest recording
    """
    if not videos:
        return {
            'status': 'NO_RECORDINGS',
            'message': 'No video files found'
        }
    
    latest_dt, latest_filename, latest_path = videos[-1]
    now = datetime.now()
    
    # Calculate expected file size for 5 minutes (rough estimate)
    # Assuming ~1-2 MB/min for typical recording = ~5-10 MB for 5 min
    try:
        file_size = latest_path.stat().st_size
        file_size_mb = file_size / (1024 * 1024)
    except Exception as e:
        file_size_mb = 0
    
    time_since_latest = now - latest_dt
    expected_interval = timedelta(minutes=interval_minutes)
    
    # Check if we're within the expected recording window
    if time_since_latest < expected_interval:
        return {
            'status': 'RECORDING',
            'latest_file': latest_filename,
            'latest_timestamp': latest_dt.isoformat(),
            'file_size_mb': round(file_size_mb, 2),
            'message': 'Camera is currently recording'
        }
    elif time_since_latest < expected_interval + timedelta(minutes=2):
        return {
            'status': 'FINISHING',
            'latest_file': latest_filename,
            'latest_timestamp': latest_dt.isoformat(),
            'file_size_mb': round(file_size_mb, 2),
            'message': 'Recent recording finishing'
        }
    else:
        minutes_ago = int(time_since_latest.total_seconds() / 60)
        return {
            'status': 'OFFLINE',
            'latest_file': latest_filename,
            'latest_timestamp': latest_dt.isoformat(),
            'file_size_mb': round(file_size_mb, 2),
            'minutes_since_last': minutes_ago,
            'message': f'No recording for {minutes_ago} minutes'
        }


def generate_report(videos: List[Tuple[datetime, str, Path]]) -> Dict:
    """
    Generate comprehensive monitoring report
    """
    offline_segments = detect_offline_segments(videos)
    latest_status = check_latest_file_status(videos)
    
    # Calculate statistics
    if videos:
        first_video = videos[0][0]
        last_video = videos[-1][0]
        date_range = {
            'first_recording': first_video.isoformat(),
            'latest_recording': last_video.isoformat(),
            'total_videos': len(videos)
        }
    else:
        date_range = {
            'first_recording': None,
            'latest_recording': None,
            'total_videos': 0
        }
    
    # Count total offline time
    total_offline_minutes = 0
    for date, segments in offline_segments.items():
        for segment in segments:
            start_time = datetime.strptime(segment['start'], '%Hh%M')
            end_time = datetime.strptime(segment['end'], '%Hh%M')
            offline_minutes = (end_time - start_time).total_seconds() / 60
            total_offline_minutes += offline_minutes
    
    return {
        'board_id': BOARD_ID,
        'timestamp': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
        'recordings_directory': RECORDINGS_DIR,
        'camera_status': latest_status,
        'offline_segments': offline_segments,
        'statistics': {
            **date_range,
            'total_offline_minutes': round(total_offline_minutes, 1),
            'total_offline_segments': sum(len(segs) for segs in offline_segments.values())
        }
    }


def main():
    """Main monitoring function"""
    global BOARD_ID
    BOARD_ID = get_board_id()
    
    print(f"📹 Recording Monitor Started")
    print(f"📂 Monitoring directory: {RECORDINGS_DIR}")
    print(f"🔍 Looking for gaps larger than {EXPECTED_INTERVAL_MINUTES} minutes (±{TOLERANCE_SECONDS}s tolerance)")
    print()
    
    # Get all video files
    videos = get_video_files(RECORDINGS_DIR)
    
    if not videos:
        print("⚠️ No video files found")
        report = {
            'board_id': BOARD_ID,
            'timestamp': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
            'recordings_directory': RECORDINGS_DIR,
            'error': 'No video files found'
        }
        print(json.dumps(report, indent=2))
        return 1
    
    print(f"✅ Found {len(videos)} video files")
    print(f"📅 Date range: {videos[0][0].date()} to {videos[-1][0].date()}")
    print()
    
    # Generate report
    report = generate_report(videos)
    
    # Print report
    print("=" * 60)
    print("MONITORING REPORT")
    print("=" * 60)
    print(json.dumps(report, indent=2))
    print("=" * 60)
    
    # Print summary
    if report['offline_segments']:
        print("\n⚠️ OFFLINE SEGMENTS DETECTED:")
        for date, segments in report['offline_segments'].items():
            print(f"\n  📅 {date}:")
            for segment in segments:
                if 'end' in segment:
                    print(f"    • {segment['start']} → {segment['end']}")
                else:
                    print(f"    • {segment['start']} (ongoing)")
    else:
        print("\n✅ No offline segments detected")
    
    print(f"\n📊 Camera Status: {report['camera_status']['status']}")
    print(f"   {report['camera_status']['message']}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

