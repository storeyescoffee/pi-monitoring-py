# Pi Monitoring Python - File Manifest

## Core Scripts

### recordings_monitor.py
**Purpose**: Main monitoring script with console output  
**Usage**: `./recordings_monitor.py`  
**Output**: Detailed JSON report to stdout  
**Dependencies**: Python 3.6+ standard library  
**Size**: ~8 KB / 329 lines

**Key Functions**:
- `get_board_id()`: Extract Raspberry Pi serial number
- `parse_filename()`: Parse video timestamp from filename
- `get_video_files()`: Scan and sort video files
- `detect_offline_segments()`: Detect gaps in recordings
- `check_latest_file_status()`: Check if currently recording
- `generate_report()`: Generate comprehensive JSON report

### main.py
**Purpose**: MQTT publishing version (entrypoint)  
**Usage**: `./main.py`  
**Output**: JSON payload published to MQTT broker  
**Dependencies**: Python 3.6+, paho-mqtt  
**Size**: ~7 KB / 255 lines

**Key Functions**:
- All from recordings_monitor.py (simplified)
- `build_payload()`: Build MQTT payload
- `publish_mqtt()`: Publish with retry logic

### test_monitor.py
**Purpose**: Test script with sample data  
**Usage**: `./test_monitor.py`  
**Output**: Demonstration with 300 test videos  
**Dependencies**: Python 3.6+ standard library  
**Size**: ~4 KB / 156 lines

**Key Functions**:
- `create_test_recordings()`: Generate test video files
- `run_test()`: Execute test scenario

## Configuration Files

### requirements.txt
**Purpose**: Python package dependencies  
**Contents**:
```
paho-mqtt>=1.6.1,<3.0.0
```

### install.sh
**Purpose**: Installation script  
**Features**:
- Check Python 3 installation
- Install `python3-paho-mqtt` via apt
- Make scripts executable
- Display usage information

### .gitignore
**Purpose**: Git ignore rules  
**Excludes**:
- Python cache files
- Virtual environments
- IDE files
- Logs
- Test directories

## Documentation Files

### README.md
**Purpose**: Complete technical documentation  
**Sections**:
- Overview and features
- Installation instructions
- Usage examples
- Configuration reference
- Output format specification
- How it works
- Troubleshooting guide
- Integration examples

**Size**: ~12 KB / 340 lines

### USAGE.md
**Purpose**: Quick start guide  
**Sections**:
- Installation
- Testing
- Basic usage
- Configuration examples
- Cron scheduling
- Output interpretation
- Troubleshooting tips
- Integration examples

**Size**: ~4 KB / 135 lines

### COMPARISON.md
**Purpose**: Bash vs Python comparison  
**Sections**:
- Feature comparison tables
- Shared architecture patterns
- Code examples side-by-side
- JSON payload structures
- Advantages of each approach
- When to use which
- Deployment together
- Migration path

**Size**: ~8 KB / 280 lines

### PROJECT_SUMMARY.md
**Purpose**: Project overview  
**Sections**:
- Project structure
- Purpose and features
- Output format
- Quick start
- Configuration
- Integration
- Testing
- Dependencies

**Size**: ~6 KB / 200 lines

### ARCHITECTURE.md
**Purpose**: Detailed architecture documentation  
**Sections**:
- System overview diagram
- Data flow (5 phases)
- Algorithm details
- File naming patterns
- JSON payload structure
- Edge cases handled
- Performance characteristics
- Configuration matrix
- Integration points
- Error handling
- Security considerations
- Future enhancements

**Size**: ~10 KB / 420 lines

### MANIFEST.md
**Purpose**: This file - complete file listing  

## Example Files

### example_output.json
**Purpose**: Example monitoring report  
**Contents**: Sample JSON output showing:
- Board ID and timestamp
- Camera status
- Offline segments (2 days)
- Latest recording info
- Statistics

## File Statistics

```
Total Files: 12
  - Python Scripts: 3
  - Shell Scripts: 1
  - Config Files: 3
  - Documentation: 5

Total Lines of Code:
  - Python: ~740 lines
  - Shell: ~40 lines
  - Documentation: ~1,500 lines

Total Size: ~60 KB
```

## Dependency Tree

```
main.py
├── paho-mqtt (external)
└── Python 3.6+ stdlib

recordings_monitor.py
└── Python 3.6+ stdlib
    ├── os
    ├── json
    ├── re
    ├── sys
    ├── datetime
    ├── pathlib
    ├── typing
    └── collections

test_monitor.py
├── recordings_monitor.py (import)
└── Python 3.6+ stdlib
    ├── tempfile
    └── shutil

install.sh
├── bash
├── python3 (system)
├── pip3 (system)
└── chmod (system)
```

## File Relationships

```
User Entry Points:
├── recordings_monitor.py (standalone)
├── main.py (production)
└── test_monitor.py (testing)

Configuration:
├── Environment variables (runtime)
└── requirements.txt (dependencies)

Setup:
└── install.sh (one-time)

Documentation (read in order):
1. PROJECT_SUMMARY.md (overview)
2. USAGE.md (quick start)
3. README.md (complete reference)
4. COMPARISON.md (design patterns)
5. ARCHITECTURE.md (deep dive)
6. MANIFEST.md (this file)
```

## Usage Scenarios

### Scenario 1: First Time Setup
```bash
1. Read: PROJECT_SUMMARY.md
2. Run: ./install.sh
3. Run: ./test_monitor.py
4. Read: USAGE.md
```

### Scenario 2: Development/Testing
```bash
1. Edit: recordings_monitor.py
2. Test: ./test_monitor.py
3. Check: example_output.json
```

### Scenario 3: Production Deployment
```bash
1. Configure: Environment variables
2. Test: ./recordings_monitor.py
3. Deploy: ./recordings_mqtt_monitor.py
4. Schedule: cron job
```

### Scenario 4: Troubleshooting
```bash
1. Check: USAGE.md → Troubleshooting
2. Check: README.md → Troubleshooting
3. Review: Logs
4. Test: ./recordings_monitor.py (manual)
```

### Scenario 5: Understanding Internals
```bash
1. Read: ARCHITECTURE.md
2. Read: recordings_monitor.py (source code)
3. Run: ./test_monitor.py (observe behavior)
```

## Integration Checklist

Before deploying to production:

- [ ] Install Python 3.6+
- [ ] Run `./install.sh`
- [ ] Test with `./test_monitor.py`
- [ ] Verify recordings directory exists
- [ ] Check video file naming matches pattern
- [ ] Test MQTT connectivity
- [ ] Configure environment variables
- [ ] Run manual test: `./recordings_monitor.py`
- [ ] Verify MQTT publish: `./main.py`
- [ ] Set up cron job
- [ ] Monitor logs for first 24 hours
- [ ] Verify MQTT messages arrive
- [ ] Check dashboard/consumer

## Maintenance Tasks

### Daily
- Monitor logs for errors
- Verify MQTT messages arriving

### Weekly
- Review offline segments
- Check disk space in recordings directory
- Verify video count increasing

### Monthly
- Review configuration
- Check for Python/dependency updates
- Review documentation for accuracy

### Quarterly
- Performance review
- Log rotation
- Backup configuration

## Version History

**v1.0** (February 2026)
- Initial release
- Basic offline detection
- MQTT publishing
- Comprehensive documentation

## File Checksums

For verification purposes:

```
Files to verify (production):
- recordings_monitor.py (executable)
- main.py (executable)
- requirements.txt (dependencies)
- install.sh (executable)

Files optional (documentation):
- README.md
- USAGE.md
- COMPARISON.md
- PROJECT_SUMMARY.md
- ARCHITECTURE.md
- MANIFEST.md
- example_output.json
- .gitignore
- test_monitor.py
```

## License & Attribution

Part of the pi-monitoring-group project.

Based on existing bash monitoring scripts:
- caisse_monitor.sh
- camera_monitor.sh
- alert_processor_monitor.sh

**Created**: February 2026  
**Language**: Python 3  
**Platform**: Raspberry Pi / Linux  
**Purpose**: Video recording monitoring

