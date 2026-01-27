# Pi Discovery

**Automated Raspberry Pi Environment Discovery System**

A comprehensive Python-based tool that discovers and documents everything about a Raspberry Pi's hardware, software, network, and peripherals. Outputs structured JSON and a beautiful HTML dashboard.

---

## Table of Contents

- [For Users](#for-users)
  - [Quick Start](#quick-start)
  - [Output Files](#output-files)
  - [Viewing the Dashboard](#viewing-the-dashboard)
  - [Refreshing Data](#refreshing-data)
  - [What Gets Discovered](#what-gets-discovered)
  - [PiSugar Battery Support](#pisugar-battery-support)
  - [Troubleshooting](#troubleshooting)
- [Demo Control Center](#demo-control-center)
  - [Starting the Demo](#starting-the-demo)
  - [Features](#features)
  - [API Reference](#api-reference)
- [For Developers](#for-developers)
  - [Project Structure](#project-structure)
  - [Architecture](#architecture)
  - [Adding New Discovery Modules](#adding-new-discovery-modules)
  - [JSON Schema](#json-schema)
  - [Dependencies](#dependencies)
  - [API Endpoints (PiSugar)](#api-endpoints-pisugar)
- [AI Agent Recreation Spec](#ai-agent-recreation-spec)

---

## For Users

### Quick Start

```bash
# Run discovery (generates JSON + HTML)
cd ~/pi_discovery
python3 discover.py

# Or use the refresh script
./refresh.sh
```

### Output Files

| File | Description |
|------|-------------|
| `pi_env.json` | Structured JSON with all discovered data |
| `pi_env.html` | Beautiful dark-themed HTML dashboard |
| `test_photo.jpg` | Camera test image (if camera detected) |
| `test_audio.wav` | Microphone test recording (if mic detected) |

### Viewing the Dashboard

**Option 1: Start the built-in web server**
```bash
./serve.sh
# Then open http://pi.local:8080/pi_env.html
```

**Option 2: Copy to your computer**
```bash
scp pi@pi.local:~/pi_discovery/pi_env.html ~/Desktop/
```

**Option 3: View directly in browser**
Open the file directly: `file:///home/pi/pi_discovery/pi_env.html`

### Refreshing Data

Run anytime to update all discovery data:
```bash
~/pi_discovery/refresh.sh
```

This regenerates both `pi_env.json` and `pi_env.html` with current system state.

### What Gets Discovered

#### Hardware
- **Pi Model**: Model name, revision, serial number, device tree info
- **CPU**: Architecture, cores, frequency (min/max/current), full lscpu output
- **Memory**: RAM total/used/available, swap usage
- **Storage**: All partitions, mount points, usage percentages, block devices
- **Temperature**: CPU temperature via vcgencmd and psutil
- **Voltages**: Core, SDRAM voltages via vcgencmd
- **GPIO**: Pin states via pinctrl, available Python libraries (gpiozero, RPi.GPIO, lgpio)

#### Peripherals
- **USB Devices**: Full lsusb output with device tree
- **Audio**: ALSA cards, capture devices (microphones), playback devices (speakers), mixer controls
- **Bluetooth**: Adapter info, paired devices
- **WiFi**: Interface details, connected network, signal strength
- **Camera**: CSI camera detection via rpicam-hello/libcamera, sensor info, supported modes
- **Display**: HDMI status, framebuffer info
- **Input Devices**: Keyboards, mice, other HID devices
- **HATs/Add-ons**: EEPROM detection, I2C scan, SPI devices
- **PiSugar Battery**: Model, charge level, voltage, current, charging status

#### Software
- **OS**: Distribution, version, kernel, uptime, boot time
- **Packages**: Count, notable packages (Python, Node, GCC, etc.)
- **Services**: Status of common services (SSH, Bluetooth, Docker, etc.)
- **Environment Variables**: Filtered for security

#### Network
- **Interfaces**: All network interfaces with IP addresses, MAC, MTU
- **Hostname**: Local hostname and FQDN
- **Gateway/DNS**: Default route and nameservers
- **Open Ports**: Listening TCP ports with PIDs

### PiSugar Battery Support

If you have a PiSugar battery, the discovery system automatically:
1. Enables I2C interface
2. Installs `pisugar-server`
3. Queries battery status via TCP API

**Manual battery commands:**
```bash
# Check battery level
echo "get battery" | nc -w 2 127.0.0.1 8423

# Check voltage
echo "get battery_v" | nc -w 2 127.0.0.1 8423

# Sync RTC
echo "rtc_pi2rtc" | nc -w 2 127.0.0.1 8423
```

**PiSugar Web UI**: http://pi.local:8421

### Troubleshooting

**Camera not detected:**
```bash
# Check if camera interface is enabled
rpicam-hello --list-cameras

# If not found, enable camera
sudo raspi-config nonint do_camera 0
sudo reboot
```

**I2C devices not found:**
```bash
# Enable I2C
sudo raspi-config nonint do_i2c 0
sudo modprobe i2c-dev
i2cdetect -y 1
```

**Audio devices not working:**
```bash
# List audio devices
arecord -l  # Capture
aplay -l    # Playback

# Test speaker
speaker-test -D plughw:0,0 -c 2 -t sine -f 440 -l 1
```

---

## Demo Control Center

The Pi Control Center is an interactive web application that lets you control your Raspberry Pi from any device on your local network. It provides a beautiful dark-themed UI with real-time system monitoring and hardware control.

### Starting the Demo

```bash
# Start the control center
cd ~/pi_discovery/demo
./run.sh

# Or run directly
python3 server.py
```

**Access from any device on your network:**
- http://pi.local:5000
- http://192.168.1.22:5000 (use your Pi's IP)

**Stop the server:**
```bash
pkill -f "python3 server.py"
```

### Features

| Feature | Description |
|---------|-------------|
| **Live System Stats** | Real-time CPU temperature, RAM usage, disk space, battery level with auto-refresh every 10 seconds |
| **Camera Stream** | Live MJPEG video stream from Pi Camera Module at 640x480 @ 15fps |
| **Photo Capture** | Take high-resolution still photos (1920x1080) and download them |
| **Camera Timelapse** | Configurable interval capture (10s to 10min), thumbnail gallery, download/clear |
| **Audio Recording** | Record audio from USB microphone (3, 5, or 10 seconds) and playback in browser |
| **Audio Visualizer** | Real-time microphone level bar with start/stop toggle |
| **Text-to-Speech** | Type any text and have the Pi speak it through the USB speaker |
| **Sound Effects** | Play beep, chime, and alert tones through the speaker |
| **Volume Control** | Adjust speaker volume with a slider (0-100%) |
| **GPIO Control** | Toggle GPIO pins 17, 22, 23, 27 with visual LED indicators |
| **File Browser** | Full filesystem navigation with breadcrumbs, preview, upload, download, delete |
| **Log Viewer** | View system logs (syslog, dmesg, auth, kernel) with filtering and auto-refresh |
| **Web Terminal** | Run safe shell commands (ls, uptime, df, etc.) directly from the browser |
| **Power Controls** | Reboot and shutdown buttons with confirmation modal |
| **Settings** | Toggle startup announcement and autostart on boot |
| **Discovery Integration** | Run full system discovery and view the dashboard |

### Demo File Structure

```
~/pi_discovery/demo/
├── index.html      # Main UI (dark-themed, responsive)
├── server.py       # Flask backend with REST API
├── run.sh          # Startup script
├── config.json     # Settings (announcement, autostart)
├── VERSION         # Version number (1.0.0)
├── timelapse/      # Timelapse image storage
└── static/
    ├── style.css   # Dark theme styling with CSS variables
    └── script.js   # Frontend JavaScript (vanilla, no frameworks)
```

### API Reference

All endpoints return JSON unless otherwise noted.

#### System Endpoints

| Endpoint | Method | Description | Response |
|----------|--------|-------------|----------|
| `/api/stats` | GET | Current system stats | `{"temperature": 45.2, "ram_percent": 65, "disk_percent": 12, "battery": 85}` |
| `/api/info` | GET | System information | `{"hostname": "pi", "model": "...", "os": "...", "ip": "...", "uptime": "..."}` |
| `/api/discovery` | GET | Full discovery JSON | Contents of `pi_env.json` |
| `/api/discovery/run` | POST | Run discovery script | `{"success": true}` |
| `/api/battery` | GET | PiSugar battery info | `{"percent": 85, "voltage": 3.95}` |

#### Camera Endpoints

| Endpoint | Method | Description | Response |
|----------|--------|-------------|----------|
| `/api/camera/stream` | GET | Live MJPEG stream | `multipart/x-mixed-replace` stream |
| `/api/camera/photo` | GET | Capture photo | JPEG image file |

#### Audio Endpoints

| Endpoint | Method | Description | Request Body |
|----------|--------|-------------|--------------|
| `/api/audio/record?duration=5` | GET | Record audio | Returns WAV file |
| `/api/audio/speak` | POST | Text-to-speech | `{"text": "Hello world"}` |
| `/api/audio/sound/<name>` | POST | Play sound (beep/chime/alert) | - |
| `/api/audio/volume` | POST | Set volume | `{"volume": 75}` |

#### GPIO Endpoints

| Endpoint | Method | Description | Request Body |
|----------|--------|-------------|--------------|
| `/api/gpio/set` | POST | Set pin state | `{"pin": 17, "state": true}` |
| `/api/gpio/blink` | POST | Blink all pins | - |
| `/api/gpio/off` | POST | Turn all pins off | - |

#### Terminal Endpoint

| Endpoint | Method | Description | Request Body |
|----------|--------|-------------|--------------|
| `/api/terminal/run` | POST | Run command | `{"command": "uptime"}` |

**Allowed commands:** `ls`, `pwd`, `date`, `uptime`, `df`, `free`, `echo`, `hostname`, `uname`, `vcgencmd`

#### File Browser Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/files/list?path=...` | GET | List directory contents |
| `/api/files/read?path=...` | GET | Read file contents (text, max 1MB) |
| `/api/files/download?path=...` | GET | Download file |
| `/api/files/upload` | POST | Upload file (multipart form with `path` field) |
| `/api/files/mkdir` | POST | Create directory `{"path": "/home/pi/newfolder"}` |
| `/api/files/delete?path=...` | DELETE | Delete file or folder |

#### Log Viewer Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/logs/sources` | GET | List available log sources |
| `/api/logs/read?source=syslog&lines=100` | GET | Read log entries |

**Log sources:** `syslog`, `dmesg`, `auth`, `pi-control-center`, `kernel`

#### Timelapse Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/timelapse/status` | GET | Get timelapse state and image list |
| `/api/timelapse/start` | POST | Start timelapse `{"interval": 60, "duration": 3600}` |
| `/api/timelapse/stop` | POST | Stop running timelapse |
| `/api/timelapse/image/<name>` | GET | Get timelapse image |
| `/api/timelapse/clear` | DELETE | Delete all timelapse images |

#### Audio Visualizer Endpoint

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/audio/levels` | GET | Get current mic level (0-100) |

#### Power Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/power/reboot` | POST | Reboot the Pi |
| `/api/power/shutdown` | POST | Shutdown the Pi |

### Demo Dependencies

```bash
# Required
sudo apt-get install -y python3-flask python3-psutil espeak-ng

# Already installed from discovery
# rpicam-apps, alsa-utils, i2c-tools
```

### Startup Announcement

When the server starts, it announces via text-to-speech:
> "Pi Control Center ready. Accessible at 192.168.1.22, port 5000."

This can be toggled on/off in the Settings section of the web UI, or by editing `config.json`:

```json
{
    "announcement_enabled": true,
    "autostart_enabled": true
}
```

### Settings (via Web UI)

The demo page includes a Settings section with toggle switches for:

| Setting | Description |
|---------|-------------|
| **Startup Announcement** | Enable/disable the TTS announcement when server starts |
| **Start on Boot** | Enable/disable auto-start via systemd service |

These settings persist in `~/pi_discovery/demo/config.json` and changes take effect immediately (for announcement) or on next boot (for autostart).

### Settings API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/settings` | GET | Get current settings |
| `/api/settings` | POST | Update settings `{"announcement_enabled": false}` |

### Security Notes

- The demo server binds to `0.0.0.0:5000` (accessible from LAN)
- Terminal commands are restricted to a safe whitelist
- Sensitive file paths are blocked
- No authentication (intended for local/home network use only)
- Do not expose to the internet without adding authentication

---

## For Developers

### Project Structure

```
~/pi_discovery/
├── discover.py      # Main discovery script (Python)
├── refresh.sh       # Shell wrapper to run discovery
├── serve.sh         # Simple HTTP server for HTML viewing
├── pi_env.json      # Output: structured JSON data
├── pi_env.html      # Output: HTML dashboard
├── test_photo.jpg   # Output: camera test (if available)
├── test_audio.wav   # Output: mic test (if available)
├── about.md         # This documentation
└── demo/            # Interactive control center
    ├── index.html   # Main UI
    ├── server.py    # Flask backend
    ├── run.sh       # Startup script
    └── static/
        ├── style.css   # Dark theme styling
        └── script.js   # Frontend JavaScript
```

### Architecture

The discovery system follows a modular architecture:

```
main()
  └── collect_all()
        ├── get_pi_model()
        ├── get_cpu_info()
        ├── get_memory_info()
        ├── get_storage_info()
        ├── get_temperature_and_voltage()
        ├── get_gpio_info()
        ├── get_usb_devices()
        ├── get_audio_devices()
        ├── get_bluetooth_info()
        ├── get_wifi_info()
        ├── get_camera_info()
        ├── get_display_info()
        ├── get_input_devices()
        ├── get_hats_and_addons()
        ├── get_pisugar_battery()
        ├── get_os_info()
        ├── get_installed_packages()
        ├── get_environment_variables()
        ├── get_services_status()
        └── get_network_info()
  └── generate_html_report()
```

Each `get_*()` function:
1. Runs system commands via `run_command()`
2. Parses output into structured dictionaries
3. Returns data for JSON serialization

### Adding New Discovery Modules

1. **Create a new function:**
```python
def get_my_peripheral():
    """Discover my new peripheral."""
    info = {"detected": False}
    
    # Run detection command
    output = run_command(["my-command", "--list"])
    if output:
        info["detected"] = True
        info["data"] = output
    
    return info
```

2. **Add to `collect_all()`:**
```python
"peripherals": {
    ...
    "my_peripheral": get_my_peripheral()
}
```

3. **Add to HTML generator (optional):**
```python
# In generate_html_report(), add a new card
my_peripheral_html = ""
if peripherals.get('my_peripheral', {}).get('detected'):
    my_peripheral_html = f'''
    <div class="card">
        <h2>🔧 My Peripheral</h2>
        <table>
            <tr><td>Data</td><td>{...}</td></tr>
        </table>
    </div>
    '''
```

### JSON Schema

```json
{
  "meta": {
    "discovery_timestamp": "ISO8601",
    "discovery_script_version": "string",
    "hostname": "string"
  },
  "hardware": {
    "pi_model": { "model": "string", "firmware_version": "string" },
    "cpu": { "architecture": "string", "cores_logical": "int", "frequency_mhz": {} },
    "memory": { "ram": { "total_mb": "float", "percent_used": "float" }, "swap": {} },
    "storage": { "partitions": [], "block_devices": {} },
    "temperature_voltage": { "temperatures": {}, "voltages": {} },
    "gpio": { "libraries": {}, "pinctrl": "string" }
  },
  "peripherals": {
    "usb": { "devices": [], "tree": "string" },
    "audio": { "capture_devices": [], "playback_devices": [], "alsa_cards": [] },
    "bluetooth": { "available": "bool", "hciconfig": "string" },
    "wifi": { "connected_network": "string", "iwconfig": "string" },
    "camera": { "detected": "bool", "cameras": [], "rpicam_output": "string" },
    "display": { "connected": "bool" },
    "input_devices": { "devices": [] },
    "hats_addons": { "detected": "bool", "i2c_scan": "string" },
    "pisugar_battery": { "detected": "bool", "battery_percent": "float", "voltage_v": "float" }
  },
  "software": {
    "os": { "pretty_name": "string", "kernel": {}, "uptime": "string" },
    "packages": { "dpkg_count": "int", "notable_packages": {} },
    "environment_variables": {},
    "services": {}
  },
  "network": {
    "hostname": "string",
    "interfaces": {},
    "listening_ports": [],
    "dns_servers": []
  }
}
```

### Dependencies

**System packages:**
- `python3` (3.9+)
- `python3-psutil`
- `i2c-tools` (for I2C scanning)
- `rpicam-apps` or `libcamera-tools` (for camera)
- `alsa-utils` (for audio)

**Optional:**
- `pisugar-server` (for PiSugar battery monitoring)

**Install all:**
```bash
sudo apt-get install -y python3-psutil i2c-tools rpicam-apps alsa-utils
```

### API Endpoints (PiSugar)

The `pisugar-server` provides a TCP API on port 8423:

| Command | Response |
|---------|----------|
| `get model` | `model: PiSugar 2 (4-LEDs)` |
| `get battery` | `battery: 85.5` (percentage) |
| `get battery_v` | `battery_v: 3.95` (volts) |
| `get battery_i` | `battery_i: -0.5` (amps, negative=discharging) |
| `get battery_charging` | `battery_charging: true/false` |
| `get battery_power_plugged` | `battery_power_plugged: true/false` |
| `get rtc_time` | `rtc_time: 2026-01-25T12:00:00` |
| `rtc_pi2rtc` | Syncs RTC to system time |

---

## AI Agent Recreation Spec

**Purpose:** Concise specification for an AI agent to recreate this project from scratch.

### Core Specification

```
PROJECT: pi_discovery
LANGUAGE: Python 3
OUTPUT: pi_env.json (structured data), pi_env.html (dashboard)
TARGET: Raspberry Pi (any model, tested on Pi Zero 2 W)

STRUCTURE:
- Single Python script (discover.py) ~1000 lines
- Helper shell scripts (refresh.sh, serve.sh)
- Self-contained HTML output (inline CSS, no external deps)

MAIN FUNCTION:
1. collect_all() -> dict with keys: meta, hardware, peripherals, software, network
2. json.dump() to pi_env.json
3. generate_html_report() -> pi_env.html

DISCOVERY FUNCTIONS (each returns dict):
- get_pi_model: cat /proc/device-tree/model, vcgencmd version
- get_cpu_info: /proc/cpuinfo, lscpu, psutil.cpu_freq()
- get_memory_info: psutil.virtual_memory(), psutil.swap_memory()
- get_storage_info: psutil.disk_partitions(), psutil.disk_usage(), lsblk -J
- get_temperature_and_voltage: vcgencmd measure_temp, vcgencmd measure_volts
- get_gpio_info: pinctrl, check for gpiozero/RPi.GPIO/lgpio imports
- get_usb_devices: lsusb, lsusb -t
- get_audio_devices: arecord -l, aplay -l, /proc/asound/cards, amixer contents
- get_bluetooth_info: hciconfig, bluetoothctl devices
- get_wifi_info: iwconfig, wpa_cli status
- get_camera_info: rpicam-hello --list-cameras (or libcamera-hello)
- get_display_info: tvservice -s, vcgencmd display_power
- get_input_devices: /proc/bus/input/devices
- get_hats_and_addons: /proc/device-tree/hat/*, i2cdetect -y 1
- get_pisugar_battery: TCP socket to 127.0.0.1:8423, query get battery/voltage/etc
- get_os_info: platform.*, /etc/os-release, uname, psutil.boot_time()
- get_installed_packages: dpkg -l count, check python3/node/gcc versions
- get_environment_variables: os.environ (filter sensitive keys)
- get_services_status: systemctl is-active for ssh/bluetooth/docker/etc
- get_network_info: psutil.net_if_addrs(), ip route, /etc/resolv.conf, psutil.net_connections()

HELPER FUNCTION:
run_command(cmd, shell=False, timeout=10) -> str or None
  - subprocess.run with capture_output=True
  - Returns stdout.strip() on success, None on failure

HTML GENERATION:
- Dark theme (--bg: #1a1a2e, --accent: #e94560)
- CSS Grid layout, responsive
- Cards for each section
- Hero stats bar (CPU cores, RAM, Storage, Temp)
- Battery bar visualization if PiSugar detected
- Inline styles only, no external dependencies
- Mobile-friendly

DEPENDENCIES:
- python3-psutil (apt install)
- Standard Pi tools: lsusb, vcgencmd, pinctrl, i2cdetect, arecord, aplay, iwconfig
- Optional: pisugar-server for battery monitoring

INSTALL STEPS:
1. mkdir ~/pi_discovery
2. Write discover.py with all get_* functions
3. Write refresh.sh (cd to dir, run python3 discover.py)
4. Write serve.sh (python3 -m http.server 8080)
5. chmod +x *.sh *.py
6. sudo apt install python3-psutil
7. Run: python3 discover.py

KEY DESIGN DECISIONS:
- All functions handle errors gracefully (return None/empty on failure)
- JSON uses indent=2 for readability
- HTML is self-contained (works offline)
- Timestamp in ISO8601 format
- Sensitive env vars filtered out
- Commands have 10s timeout by default
- Camera detection uses modern rpicam-* tools first, fallback to libcamera-*

DEMO CONTROL CENTER (demo/ folder):
- Flask web server on port 5000
- REST API for all Pi hardware interactions
- Frontend: index.html + static/style.css + static/script.js
- Dark theme matching main dashboard
- Uses Font Awesome icons from CDN
- MJPEG camera streaming via rpicam-vid
- Audio recording via arecord, playback via aplay
- TTS via espeak-ng piped to aplay
- GPIO state tracked in Python dict (real control with gpiozero if available)
- Terminal with command whitelist for security
- No external JS frameworks (vanilla JavaScript)

DEMO API ENDPOINTS:
- GET /api/stats -> {temperature, ram_percent, disk_percent, battery}
- GET /api/info -> {hostname, model, os, ip, uptime}
- GET /api/camera/stream -> MJPEG multipart stream
- GET /api/camera/photo -> JPEG file
- GET /api/audio/record?duration=N -> WAV file
- GET /api/audio/levels -> {level: 0-100} for visualizer
- POST /api/audio/speak {text} -> TTS
- POST /api/audio/sound/<name> -> play beep/chime/alert
- POST /api/gpio/set {pin, state} -> toggle GPIO
- POST /api/terminal/run {command} -> run whitelisted command
- GET /api/settings -> {announcement_enabled, autostart_enabled}
- POST /api/settings {setting: value} -> update settings
- GET /api/files/list?path=... -> directory listing
- GET /api/files/read?path=... -> file contents
- GET /api/files/download?path=... -> file download
- POST /api/files/upload -> multipart file upload
- POST /api/files/mkdir {path} -> create directory
- DELETE /api/files/delete?path=... -> delete file/folder
- GET /api/logs/read?source=syslog&lines=100 -> log entries
- GET /api/timelapse/status -> {running, count, images}
- POST /api/timelapse/start {interval, duration} -> start capture
- POST /api/timelapse/stop -> stop capture
- GET /api/timelapse/image/<name> -> get image
- DELETE /api/timelapse/clear -> delete all images
- POST /api/power/reboot -> reboot Pi
- POST /api/power/shutdown -> shutdown Pi

DEMO SETTINGS:
- config.json stores: announcement_enabled (bool), autostart_enabled (bool)
- Startup announcement: TTS via espeak-ng piped to aplay, runs in background thread after 4s delay
- Autostart toggle: enables/disables systemd service via sudo systemctl (requires sudoers rule)
- sudoers.d/pi-control-center: allows pi user to enable/disable, reboot, poweroff without password
- VERSION file contains semver (1.0.0)
```

### Minimal Reproduction Commands

```bash
# On a fresh Raspberry Pi:
sudo apt update && sudo apt install -y python3-psutil i2c-tools

mkdir -p ~/pi_discovery
cd ~/pi_discovery

# Create discover.py with:
# - run_command() helper
# - ~20 get_*() discovery functions
# - collect_all() aggregator
# - generate_html_report() for HTML output
# - main() that calls collect_all(), saves JSON, generates HTML

# Create refresh.sh:
echo '#!/bin/bash
cd "$(dirname "$0")" && python3 discover.py' > refresh.sh
chmod +x refresh.sh

# Create serve.sh:
echo '#!/bin/bash
cd "$(dirname "$0")" && python3 -m http.server ${1:-8080}' > serve.sh
chmod +x serve.sh

# Run discovery
python3 discover.py

# View results
cat pi_env.json | python3 -m json.tool | head -50
```

---

## License

This project is provided as-is for personal/hobby use. Feel free to modify and extend.

## Credits

Created for Raspberry Pi Zero 2 W running Debian Trixie, with support for:
- [Raspberry Pi Camera Module v2](https://www.raspberrypi.com/products/camera-module-v2/)
- [Adafruit Mini USB Microphone](https://www.adafruit.com/product/3367)
- [Adafruit Mini External USB Stereo Speaker](https://www.adafruit.com/product/3369)
- [PiSugar 2 Battery](https://www.pisugar.com/)
