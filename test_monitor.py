#!/usr/bin/env python3
"""
Test script to demonstrate the recordings monitor with sample data
Creates a temporary directory with sample video files (empty files for testing)
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta

# Import the monitor functions
sys.path.insert(0, os.path.dirname(__file__))
from recordings_monitor import (
    get_video_files,
    detect_offline_segments,
    check_latest_file_status,
    generate_report
)


def create_test_recordings(test_dir: Path, start_time: datetime, 
                          num_videos: int = 50,
                          gaps: list = None):
    """
    Create test video files with specific timestamps
    
    Args:
        test_dir: Directory to create files in
        start_time: Starting timestamp
        num_videos: Number of videos to create
        gaps: List of (index, gap_minutes) tuples to create offline segments
    """
    if gaps is None:
        gaps = []
    
    current_time = start_time
    gap_dict = dict(gaps)
    
    for i in range(num_videos):
        # Check if we should add a gap after this video
        if i in gap_dict:
            gap_minutes = gap_dict[i]
            current_time += timedelta(minutes=gap_minutes)
        
        # Format filename: DDMMYYYY_HHMMSS.mp4
        filename = current_time.strftime('%d%m%Y_%H%M%S.mp4')
        filepath = test_dir / filename
        
        # Create empty file (or with minimal content)
        with open(filepath, 'wb') as f:
            # Write a small amount of data to simulate file size
            f.write(b'\x00' * (1024 * 1024 * 8))  # 8 MB
        
        # Move to next interval (5 minutes)
        current_time += timedelta(minutes=5)
    
    print(f"✅ Created {num_videos} test video files in {test_dir}")


def run_test():
    """Run test with sample data"""
    print("=" * 70)
    print("RECORDINGS MONITOR TEST")
    print("=" * 70)
    print()
    
    # Create temporary directory
    test_dir = Path(tempfile.mkdtemp(prefix='recordings_test_'))
    print(f"📂 Test directory: {test_dir}")
    print()
    
    try:
        # Create test scenario with gaps
        # Start: February 9, 2026 at 00:00:00
        start_time = datetime(2026, 2, 9, 0, 0, 0)
        
        print("📹 Creating test scenario...")
        print("   - Normal recordings from 00:00 to 08:35")
        print("   - 30-minute gap (offline) from 08:40 to 09:10")
        print("   - Normal recordings from 09:10 to 17:05")
        print("   - 1-hour gap (offline) from 17:10 to 18:10")
        print("   - Normal recordings from 18:10 to next day")
        print()
        
        # Create videos with specific gaps
        # Gap 1: After video at 08:35, skip to 09:10 (30 min gap)
        # Gap 2: After video at 17:05, skip to 18:10 (1 hour gap)
        
        gaps = [
            (103, 30),   # After ~8h35 (103 * 5min), add 30min gap
            (250, 60),   # After ~17h05, add 60min gap
        ]
        
        create_test_recordings(test_dir, start_time, num_videos=300, gaps=gaps)
        
        # Run monitoring
        print()
        print("🔍 Analyzing recordings...")
        print()
        
        videos = get_video_files(str(test_dir))
        
        if videos:
            print(f"✅ Found {len(videos)} video files")
            print(f"📅 Date range: {videos[0][0]} to {videos[-1][0]}")
            print()
            
            # Generate report
            import json
            
            # Temporarily override BOARD_ID for test
            import recordings_monitor
            recordings_monitor.BOARD_ID = "TEST_BOARD_12345678"
            recordings_monitor.RECORDINGS_DIR = str(test_dir)
            
            report = generate_report(videos)
            
            print("=" * 70)
            print("MONITORING REPORT")
            print("=" * 70)
            print(json.dumps(report, indent=2))
            print("=" * 70)
            
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
            print()
            print(f"📈 Statistics:")
            print(f"   Total videos: {report['statistics']['total_videos']}")
            print(f"   Offline segments: {report['statistics']['total_offline_segments']}")
            print(f"   Total offline time: {report['statistics']['total_offline_minutes']} minutes")
        
        print()
        print("=" * 70)
        print("TEST COMPLETED SUCCESSFULLY")
        print("=" * 70)
        
    finally:
        # Cleanup
        print()
        print(f"🧹 Cleaning up test directory...")
        shutil.rmtree(test_dir)
        print(f"✅ Test directory removed")


if __name__ == '__main__':
    try:
        run_test()
    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

