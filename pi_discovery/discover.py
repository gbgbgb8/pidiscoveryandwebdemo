#!/usr/bin/env python3
"""
Raspberry Pi Environment Discovery Script
Collects comprehensive information about hardware, software, network, and peripherals.
Outputs structured JSON to pi_env.json
"""

import json
import os
import subprocess
import socket
import platform
import re
from datetime import datetime
from pathlib import Path

try:
    import psutil
except ImportError:
    print("Installing psutil...")
    subprocess.run(["sudo", "apt-get", "install", "-y", "python3-psutil"], check=True)
    import psutil


def run_command(cmd, shell=False, timeout=10):
    """Run a shell command and return output, or None on failure."""
    try:
        if shell:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        else:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip() if result.returncode == 0 else None
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
        return None


def get_cpu_info():
    """Gather CPU information."""
    cpu_info = {
        "architecture": platform.machine(),
        "processor": platform.processor(),
        "cores_physical": psutil.cpu_count(logical=False),
        "cores_logical": psutil.cpu_count(logical=True),
        "frequency_mhz": None,
        "model": None,
        "hardware": None,
        "revision": None,
        "serial": None,
    }
    
    # Parse /proc/cpuinfo for Pi-specific details
    cpuinfo = run_command(["cat", "/proc/cpuinfo"])
    if cpuinfo:
        for line in cpuinfo.split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip().lower()
                value = value.strip()
                if key == "model name":
                    cpu_info["model"] = value
                elif key == "hardware":
                    cpu_info["hardware"] = value
                elif key == "revision":
                    cpu_info["revision"] = value
                elif key == "serial":
                    cpu_info["serial"] = value
    
    # Get CPU frequency
    freq = psutil.cpu_freq()
    if freq:
        cpu_info["frequency_mhz"] = {
            "current": freq.current,
            "min": freq.min,
            "max": freq.max
        }
    
    # lscpu output
    lscpu = run_command(["lscpu"])
    if lscpu:
        cpu_info["lscpu_raw"] = lscpu
    
    return cpu_info


def get_memory_info():
    """Gather memory information."""
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    
    return {
        "ram": {
            "total_bytes": mem.total,
            "total_mb": round(mem.total / (1024 * 1024), 2),
            "available_mb": round(mem.available / (1024 * 1024), 2),
            "used_mb": round(mem.used / (1024 * 1024), 2),
            "percent_used": mem.percent
        },
        "swap": {
            "total_mb": round(swap.total / (1024 * 1024), 2),
            "used_mb": round(swap.used / (1024 * 1024), 2),
            "percent_used": swap.percent
        }
    }


def get_storage_info():
    """Gather storage information."""
    partitions = []
    for part in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(part.mountpoint)
            partitions.append({
                "device": part.device,
                "mountpoint": part.mountpoint,
                "fstype": part.fstype,
                "total_gb": round(usage.total / (1024**3), 2),
                "used_gb": round(usage.used / (1024**3), 2),
                "free_gb": round(usage.free / (1024**3), 2),
                "percent_used": usage.percent
            })
        except PermissionError:
            continue
    
    # Get block devices
    lsblk = run_command(["lsblk", "-o", "NAME,SIZE,TYPE,MOUNTPOINT", "-J"])
    block_devices = None
    if lsblk:
        try:
            block_devices = json.loads(lsblk)
        except json.JSONDecodeError:
            pass
    
    return {
        "partitions": partitions,
        "block_devices": block_devices
    }


def get_pi_model():
    """Get Raspberry Pi model information."""
    model = run_command(["cat", "/proc/device-tree/model"])
    if model:
        model = model.replace("\x00", "")  # Remove null bytes
    
    # Additional Pi-specific info
    pi_info = {
        "model": model,
        "device_tree_compatible": run_command(["cat", "/proc/device-tree/compatible"]),
    }
    
    # vcgencmd for Pi-specific data
    vcgencmd_version = run_command(["vcgencmd", "version"])
    if vcgencmd_version:
        pi_info["firmware_version"] = vcgencmd_version
    
    return pi_info


def get_temperature_and_voltage():
    """Get temperature and voltage readings."""
    temps = {}
    voltages = {}
    
    # CPU temperature via psutil
    try:
        psutil_temps = psutil.sensors_temperatures()
        if psutil_temps:
            temps["psutil"] = {k: [{"label": s.label, "current": s.current, "high": s.high, "critical": s.critical} 
                                   for s in v] for k, v in psutil_temps.items()}
    except Exception:
        pass
    
    # vcgencmd temperature
    temp = run_command(["vcgencmd", "measure_temp"])
    if temp:
        match = re.search(r"temp=(\d+\.?\d*)", temp)
        if match:
            temps["cpu_celsius"] = float(match.group(1))
    
    # vcgencmd voltages
    for volt_id in ["core", "sdram_c", "sdram_i", "sdram_p"]:
        volt = run_command(["vcgencmd", "measure_volts", volt_id])
        if volt:
            match = re.search(r"volt=(\d+\.?\d*)", volt)
            if match:
                voltages[volt_id] = float(match.group(1))
    
    # Throttled status
    throttled = run_command(["vcgencmd", "get_throttled"])
    
    return {
        "temperatures": temps,
        "voltages": voltages,
        "throttled_status": throttled
    }


def get_gpio_info():
    """Get GPIO pin information."""
    gpio_info = {}
    
    # Check if raspi-gpio is available
    raspi_gpio = run_command(["raspi-gpio", "get"])
    if raspi_gpio:
        gpio_info["raspi_gpio"] = raspi_gpio
    
    # Check for GPIO libraries
    gpio_info["libraries"] = {
        "rpi_gpio_available": Path("/usr/lib/python3/dist-packages/RPi").exists(),
        "gpiozero_available": run_command(["python3", "-c", "import gpiozero"]) is not None,
        "lgpio_available": run_command(["python3", "-c", "import lgpio"]) is not None,
    }
    
    # Check pinctrl
    pinctrl = run_command(["pinctrl"])
    if pinctrl:
        gpio_info["pinctrl"] = pinctrl
    
    return gpio_info


def get_usb_devices():
    """Get USB device information."""
    lsusb = run_command(["lsusb"])
    lsusb_verbose = run_command(["lsusb", "-t"])
    
    devices = []
    if lsusb:
        for line in lsusb.split("\n"):
            if line.strip():
                devices.append(line.strip())
    
    return {
        "devices": devices,
        "tree": lsusb_verbose
    }


def get_audio_devices():
    """Get audio device information (microphones, speakers)."""
    audio_info = {
        "capture_devices": [],
        "playback_devices": [],
        "alsa_cards": []
    }
    
    # Get ALSA cards
    cards = run_command(["cat", "/proc/asound/cards"])
    if cards:
        audio_info["alsa_cards_raw"] = cards
        for line in cards.split("\n"):
            line = line.strip()
            if line and line[0].isdigit():
                # Parse card line like " 0 [Device         ]: USB-Audio - USB PnP Sound Device"
                match = re.match(r"(\d+)\s+\[(\w+)\s*\]:\s+(.+)", line)
                if match:
                    audio_info["alsa_cards"].append({
                        "card_id": match.group(1),
                        "name": match.group(2),
                        "type": match.group(3)
                    })
    
    # Get capture devices (microphones)
    arecord = run_command(["arecord", "-l"])
    if arecord:
        audio_info["arecord_raw"] = arecord
        for line in arecord.split("\n"):
            if line.startswith("card"):
                # Parse: "card 0: Device [USB PnP Sound Device], device 0: USB Audio [USB Audio]"
                match = re.match(r"card (\d+): (\w+) \[([^\]]+)\], device (\d+): (.+)", line)
                if match:
                    audio_info["capture_devices"].append({
                        "card": match.group(1),
                        "card_name": match.group(2),
                        "card_desc": match.group(3),
                        "device": match.group(4),
                        "device_desc": match.group(5)
                    })
    
    # Get playback devices (speakers)
    aplay = run_command(["aplay", "-l"])
    if aplay:
        audio_info["aplay_raw"] = aplay
        for line in aplay.split("\n"):
            if line.startswith("card"):
                match = re.match(r"card (\d+): (\w+) \[([^\]]+)\], device (\d+): (.+)", line)
                if match:
                    audio_info["playback_devices"].append({
                        "card": match.group(1),
                        "card_name": match.group(2),
                        "card_desc": match.group(3),
                        "device": match.group(4),
                        "device_desc": match.group(5)
                    })
    
    # Get mixer controls for capture devices
    for card in audio_info["alsa_cards"]:
        mixer = run_command(["amixer", "-c", card["card_id"], "contents"])
        if mixer:
            controls = {}
            current_control = None
            for line in mixer.split("\n"):
                if line.startswith("numid="):
                    # Parse control name
                    name_match = re.search(r"name='([^']+)'", line)
                    if name_match:
                        current_control = name_match.group(1)
                        controls[current_control] = {}
                elif current_control and ": values=" in line:
                    val_match = re.search(r": values=(.+)", line)
                    if val_match:
                        controls[current_control]["value"] = val_match.group(1)
            if controls:
                card["mixer_controls"] = controls
    
    return audio_info


def get_bluetooth_info():
    """Get Bluetooth information."""
    bt_info = {
        "available": False,
        "devices": []
    }
    
    # Check if bluetooth is available
    hciconfig = run_command(["hciconfig"])
    if hciconfig and "hci" in hciconfig.lower():
        bt_info["available"] = True
        bt_info["hciconfig"] = hciconfig
    
    # Check bluetoothctl
    bt_devices = run_command("bluetoothctl devices 2>/dev/null", shell=True)
    if bt_devices:
        bt_info["paired_devices"] = bt_devices.split("\n")
    
    return bt_info


def get_wifi_info():
    """Get WiFi information."""
    wifi_info = {
        "interfaces": [],
        "connected_network": None
    }
    
    # iwconfig output
    iwconfig = run_command(["iwconfig"], timeout=5)
    if iwconfig:
        wifi_info["iwconfig"] = iwconfig
    
    # Current connection
    nmcli = run_command(["nmcli", "-t", "-f", "active,ssid", "dev", "wifi"])
    if nmcli:
        for line in nmcli.split("\n"):
            if line.startswith("yes:"):
                wifi_info["connected_network"] = line.split(":", 1)[1]
                break
    
    # Alternative: wpa_cli
    wpa_status = run_command(["wpa_cli", "-i", "wlan0", "status"])
    if wpa_status:
        wifi_info["wpa_status"] = wpa_status
    
    return wifi_info


def get_camera_info():
    """Get camera information."""
    camera_info = {
        "detected": False,
        "cameras": []
    }
    
    # rpicam-hello detect (modern libcamera-based tool)
    rpicam = run_command(["rpicam-hello", "--list-cameras"], timeout=15)
    if rpicam:
        camera_info["rpicam_output"] = rpicam
        if "Available cameras" in rpicam:
            camera_info["detected"] = True
            # Parse camera info
            lines = rpicam.split("\n")
            for line in lines:
                if " : " in line and not line.startswith("-"):
                    # e.g., "0 : imx219 [3280x2464 10-bit RGGB]"
                    parts = line.split(" : ", 1)
                    if len(parts) == 2:
                        cam_id = parts[0].strip()
                        cam_desc = parts[1].strip()
                        # Extract sensor name
                        sensor = cam_desc.split()[0] if cam_desc else "unknown"
                        camera_info["cameras"].append({
                            "id": cam_id,
                            "sensor": sensor,
                            "description": cam_desc
                        })
    
    # Fallback: libcamera-hello
    if not camera_info["detected"]:
        libcamera = run_command(["libcamera-hello", "--list-cameras"], timeout=15)
        if libcamera:
            camera_info["libcamera_output"] = libcamera
            if "Available cameras" in libcamera:
                camera_info["detected"] = True
    
    # vcgencmd check (legacy, may show supported=0 for libcamera stack)
    vcgencmd_cam = run_command(["vcgencmd", "get_camera"])
    if vcgencmd_cam:
        camera_info["vcgencmd"] = vcgencmd_cam
    
    # Check /dev/video devices
    video_devices = list(Path("/dev").glob("video*"))
    camera_info["video_devices"] = [str(v) for v in video_devices]
    
    return camera_info


def get_os_info():
    """Get OS and kernel information."""
    os_info = {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "node": platform.node(),
        "python_version": platform.python_version(),
    }
    
    # Parse os-release
    os_release = run_command(["cat", "/etc/os-release"])
    if os_release:
        for line in os_release.split("\n"):
            if "=" in line:
                key, value = line.split("=", 1)
                os_info[key.lower()] = value.strip('"')
    
    # Kernel info
    os_info["kernel"] = {
        "version": run_command(["uname", "-r"]),
        "full": run_command(["uname", "-a"])
    }
    
    # Uptime
    uptime = run_command(["uptime", "-p"])
    if uptime:
        os_info["uptime"] = uptime
    
    # Boot time
    boot_time = datetime.fromtimestamp(psutil.boot_time())
    os_info["boot_time"] = boot_time.isoformat()
    
    return os_info


def get_installed_packages():
    """Get information about installed packages."""
    packages = {
        "dpkg_count": 0,
        "notable_packages": {}
    }
    
    # Count installed packages
    dpkg_list = run_command("dpkg -l | grep '^ii' | wc -l", shell=True)
    if dpkg_list:
        packages["dpkg_count"] = int(dpkg_list)
    
    # Check for notable tools/languages
    notable = {
        "python3": run_command(["python3", "--version"]),
        "python2": run_command(["python2", "--version"]),
        "node": run_command(["node", "--version"]),
        "npm": run_command(["npm", "--version"]),
        "git": run_command(["git", "--version"]),
        "gcc": run_command(["gcc", "--version"]),
        "make": run_command(["make", "--version"]),
        "docker": run_command(["docker", "--version"]),
        "nginx": run_command(["nginx", "-v"]),
        "apache2": run_command(["apache2", "-v"]),
        "pip3": run_command(["pip3", "--version"]),
        "java": run_command(["java", "-version"]),
        "ruby": run_command(["ruby", "--version"]),
        "go": run_command(["go", "version"]),
        "rust": run_command(["rustc", "--version"]),
    }
    
    packages["notable_packages"] = {k: v for k, v in notable.items() if v}
    
    return packages


def get_environment_variables():
    """Get environment variables (filtered for security)."""
    # Filter out potentially sensitive variables
    sensitive_patterns = ["password", "secret", "key", "token", "credential", "auth"]
    
    env_vars = {}
    for key, value in os.environ.items():
        if not any(pattern in key.lower() for pattern in sensitive_patterns):
            env_vars[key] = value
    
    return env_vars


def get_network_info():
    """Get network information."""
    network = {
        "hostname": socket.gethostname(),
        "fqdn": socket.getfqdn(),
        "interfaces": {}
    }
    
    # Get network interfaces with psutil
    addrs = psutil.net_if_addrs()
    stats = psutil.net_if_stats()
    
    for iface, addr_list in addrs.items():
        network["interfaces"][iface] = {
            "addresses": [],
            "is_up": stats.get(iface, {}).isup if hasattr(stats.get(iface, {}), 'isup') else None,
            "speed": getattr(stats.get(iface, {}), 'speed', None),
            "mtu": getattr(stats.get(iface, {}), 'mtu', None)
        }
        for addr in addr_list:
            network["interfaces"][iface]["addresses"].append({
                "family": str(addr.family),
                "address": addr.address,
                "netmask": addr.netmask,
                "broadcast": addr.broadcast
            })
    
    # Get default gateway
    gateway = run_command(["ip", "route", "show", "default"])
    if gateway:
        network["default_gateway"] = gateway
    
    # Open ports (listening)
    connections = psutil.net_connections(kind='inet')
    listening_ports = []
    for conn in connections:
        if conn.status == 'LISTEN':
            listening_ports.append({
                "port": conn.laddr.port,
                "address": conn.laddr.ip,
                "pid": conn.pid
            })
    network["listening_ports"] = listening_ports
    
    # DNS servers
    resolv = run_command(["cat", "/etc/resolv.conf"])
    if resolv:
        dns_servers = re.findall(r"nameserver\s+(\S+)", resolv)
        network["dns_servers"] = dns_servers
    
    return network


def get_display_info():
    """Get display/monitor information."""
    display = {
        "connected": False,
        "displays": []
    }
    
    # Check DISPLAY environment variable
    display["display_env"] = os.environ.get("DISPLAY")
    
    # tvservice for HDMI
    tvservice = run_command(["tvservice", "-s"])
    if tvservice:
        display["tvservice"] = tvservice
        if "HDMI" in tvservice or "DMT" in tvservice or "CEA" in tvservice:
            display["connected"] = True
    
    # vcgencmd display info
    display_id = run_command(["vcgencmd", "display_power"])
    if display_id:
        display["display_power"] = display_id
    
    # Framebuffer info
    fb_info = run_command(["cat", "/sys/class/graphics/fb0/virtual_size"])
    if fb_info:
        display["framebuffer_size"] = fb_info
    
    return display


def get_input_devices():
    """Get keyboard, mouse, and other input devices."""
    inputs = {
        "devices": []
    }
    
    # List input devices
    input_devices = run_command(["cat", "/proc/bus/input/devices"])
    if input_devices:
        inputs["raw"] = input_devices
        # Parse for device names
        for block in input_devices.split("\n\n"):
            name_match = re.search(r'Name="([^"]+)"', block)
            if name_match:
                inputs["devices"].append(name_match.group(1))
    
    return inputs


def get_pisugar_battery():
    """Get PiSugar battery information if available."""
    battery_info = {
        "detected": False,
        "model": None,
        "battery_percent": None,
        "voltage_v": None,
        "current_a": None,
        "charging": None,
        "power_plugged": None
    }
    
    # Check if pisugar-server is running
    pisugar_status = run_command(["systemctl", "is-active", "pisugar-server"])
    if pisugar_status != "active":
        return battery_info
    
    # Query PiSugar server via TCP
    def pisugar_query(cmd):
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect(("127.0.0.1", 8423))
            s.send((cmd + "\n").encode())
            response = s.recv(1024).decode().strip()
            s.close()
            if ": " in response:
                return response.split(": ", 1)[1]
            return response
        except Exception:
            return None
    
    model = pisugar_query("get model")
    if model:
        battery_info["detected"] = True
        battery_info["model"] = model
        
        # Get battery details
        battery = pisugar_query("get battery")
        if battery:
            try:
                battery_info["battery_percent"] = float(battery)
            except ValueError:
                pass
        
        voltage = pisugar_query("get battery_v")
        if voltage:
            try:
                battery_info["voltage_v"] = round(float(voltage), 3)
            except ValueError:
                pass
        
        current = pisugar_query("get battery_i")
        if current:
            try:
                battery_info["current_a"] = round(float(current), 3)
            except ValueError:
                pass
        
        charging = pisugar_query("get battery_charging")
        battery_info["charging"] = charging == "true" if charging else None
        
        plugged = pisugar_query("get battery_power_plugged")
        battery_info["power_plugged"] = plugged == "true" if plugged else None
        
        # Additional info
        battery_info["input_protect"] = pisugar_query("get battery_input_protect_enabled")
        battery_info["safe_shutdown_level"] = pisugar_query("get auto_shutdown_level")
    
    return battery_info


def get_hats_and_addons():
    """Detect HATs and add-on boards."""
    hats = {
        "detected": False,
        "info": None
    }
    
    # Check HAT EEPROM
    hat_info = run_command(["cat", "/proc/device-tree/hat/product"])
    if hat_info:
        hats["detected"] = True
        hats["info"] = {
            "product": hat_info.replace("\x00", ""),
            "vendor": run_command(["cat", "/proc/device-tree/hat/vendor"]),
            "uuid": run_command(["cat", "/proc/device-tree/hat/uuid"]),
        }
        # Clean null bytes
        for key in hats["info"]:
            if hats["info"][key]:
                hats["info"][key] = hats["info"][key].replace("\x00", "")
    
    # I2C devices (common for sensors/HATs)
    i2c_devices = run_command(["i2cdetect", "-y", "1"])
    if i2c_devices:
        hats["i2c_scan"] = i2c_devices
    
    # SPI devices
    spi_devices = list(Path("/dev").glob("spidev*"))
    hats["spi_devices"] = [str(s) for s in spi_devices]
    
    return hats


def get_services_status():
    """Get status of common services."""
    services = {}
    
    common_services = [
        "ssh", "sshd", "bluetooth", "avahi-daemon", 
        "NetworkManager", "wpa_supplicant", "cron",
        "docker", "nginx", "apache2", "pigpiod"
    ]
    
    for service in common_services:
        status = run_command(["systemctl", "is-active", service])
        services[service] = status if status else "not-found"
    
    return services


def collect_all():
    """Collect all discovery information."""
    print("Starting Raspberry Pi environment discovery...")
    
    discovery = {
        "meta": {
            "discovery_timestamp": datetime.now().isoformat(),
            "discovery_script_version": "1.0.0",
            "hostname": socket.gethostname()
        },
        "hardware": {
            "pi_model": get_pi_model(),
            "cpu": get_cpu_info(),
            "memory": get_memory_info(),
            "storage": get_storage_info(),
            "temperature_voltage": get_temperature_and_voltage(),
            "gpio": get_gpio_info()
        },
        "peripherals": {
            "usb": get_usb_devices(),
            "audio": get_audio_devices(),
            "bluetooth": get_bluetooth_info(),
            "wifi": get_wifi_info(),
            "camera": get_camera_info(),
            "display": get_display_info(),
            "input_devices": get_input_devices(),
            "hats_addons": get_hats_and_addons(),
            "pisugar_battery": get_pisugar_battery()
        },
        "software": {
            "os": get_os_info(),
            "packages": get_installed_packages(),
            "environment_variables": get_environment_variables(),
            "services": get_services_status()
        },
        "network": get_network_info()
    }
    
    return discovery


def generate_html_report(discovery, output_path):
    """Generate a nice HTML report from the discovery data."""
    
    # Helper to safely get nested values
    def get(d, *keys, default="N/A"):
        for key in keys:
            if isinstance(d, dict) and key in d:
                d = d[key]
            else:
                return default
        return d if d is not None else default
    
    # Get key values
    pi_model = get(discovery, 'hardware', 'pi_model', 'model', default='Unknown')
    hostname = get(discovery, 'meta', 'hostname')
    timestamp = get(discovery, 'meta', 'discovery_timestamp')
    
    cpu = discovery.get('hardware', {}).get('cpu', {})
    mem = discovery.get('hardware', {}).get('memory', {}).get('ram', {})
    temp_data = discovery.get('hardware', {}).get('temperature_voltage', {})
    temp = temp_data.get('temperatures', {}).get('cpu_celsius', 'N/A')
    
    storage = discovery.get('hardware', {}).get('storage', {}).get('partitions', [])
    root_storage = next((p for p in storage if p.get('mountpoint') == '/'), storage[0] if storage else {})
    
    os_info = discovery.get('software', {}).get('os', {})
    packages = discovery.get('software', {}).get('packages', {})
    services = discovery.get('software', {}).get('services', {})
    
    network = discovery.get('network', {})
    peripherals = discovery.get('peripherals', {})
    
    # Get IP addresses
    ip_addresses = []
    for iface, info in network.get('interfaces', {}).items():
        for addr in info.get('addresses', []):
            if 'AF_INET' in str(addr.get('family', '')) and not addr.get('address', '').startswith('127.'):
                ip_addresses.append(f"{iface}: {addr['address']}")
    
    # Battery info
    battery = peripherals.get('pisugar_battery', {})
    battery_html = ""
    if battery.get('detected'):
        battery_percent = battery.get('battery_percent', 0)
        battery_color = "#4CAF50" if battery_percent > 50 else "#FFC107" if battery_percent > 20 else "#f44336"
        charging_icon = "⚡" if battery.get('charging') else "🔋"
        battery_html = f'''
        <div class="card">
            <h2>🔋 Battery (PiSugar)</h2>
            <div class="battery-bar">
                <div class="battery-level" style="width: {battery_percent}%; background: {battery_color};"></div>
            </div>
            <table>
                <tr><td>Model</td><td>{battery.get('model', 'N/A')}</td></tr>
                <tr><td>Level</td><td>{charging_icon} {battery_percent}%</td></tr>
                <tr><td>Voltage</td><td>{battery.get('voltage_v', 'N/A')} V</td></tr>
                <tr><td>Current</td><td>{battery.get('current_a', 'N/A')} A</td></tr>
                <tr><td>Charging</td><td>{'Yes' if battery.get('charging') else 'No'}</td></tr>
                <tr><td>Power Plugged</td><td>{'Yes' if battery.get('power_plugged') else 'No'}</td></tr>
            </table>
        </div>
        '''
    
    # Camera info
    camera = peripherals.get('camera', {})
    camera_html = ""
    if camera.get('detected'):
        cameras = camera.get('cameras', [])
        cam_info = cameras[0] if cameras else {}
        camera_html = f'''
        <div class="card">
            <h2>📷 Camera</h2>
            <table>
                <tr><td>Sensor</td><td>{cam_info.get('sensor', 'Unknown')}</td></tr>
                <tr><td>Description</td><td>{cam_info.get('description', 'N/A')}</td></tr>
            </table>
        </div>
        '''
    
    # Audio devices
    audio = peripherals.get('audio', {})
    audio_rows = ""
    for card in audio.get('alsa_cards', []):
        card_type = "🎤 Mic" if "Capture" in str(card.get('mixer_controls', {})) else "🔊 Speaker"
        audio_rows += f"<tr><td>Card {card.get('card_id')}</td><td>{card_type}</td><td>{card.get('type', 'Unknown')}</td></tr>"
    
    audio_html = f'''
    <div class="card">
        <h2>🔊 Audio Devices</h2>
        <table>
            <tr><th>Card</th><th>Type</th><th>Description</th></tr>
            {audio_rows}
        </table>
    </div>
    ''' if audio_rows else ""
    
    # USB devices
    usb = peripherals.get('usb', {})
    usb_rows = "".join(f"<tr><td>{dev}</td></tr>" for dev in usb.get('devices', []))
    usb_html = f'''
    <div class="card">
        <h2>🔌 USB Devices</h2>
        <table>
            {usb_rows}
        </table>
    </div>
    ''' if usb_rows else ""
    
    # Services
    active_services = [s for s, status in services.items() if status == 'active']
    inactive_services = [s for s, status in services.items() if status != 'active' and status != 'not-found']
    
    # GPIO libraries
    gpio = discovery.get('hardware', {}).get('gpio', {}).get('libraries', {})
    gpio_libs = []
    if gpio.get('gpiozero_available'): gpio_libs.append("gpiozero")
    if gpio.get('rpi_gpio_available'): gpio_libs.append("RPi.GPIO")
    if gpio.get('lgpio_available'): gpio_libs.append("lgpio")
    
    # Notable packages
    notable = packages.get('notable_packages', {})
    pkg_rows = "".join(f"<tr><td>{k}</td><td>{v.split(chr(10))[0] if v else 'N/A'}</td></tr>" for k, v in notable.items())
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pi Discovery - {hostname}</title>
    <style>
        :root {{
            --bg: #1a1a2e;
            --card-bg: #16213e;
            --accent: #e94560;
            --text: #eaeaea;
            --text-dim: #a0a0a0;
            --success: #4CAF50;
            --warning: #FFC107;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
            padding: 20px;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        header {{
            text-align: center;
            padding: 30px 0;
            border-bottom: 2px solid var(--accent);
            margin-bottom: 30px;
        }}
        header h1 {{
            font-size: 2.5em;
            color: var(--accent);
            margin-bottom: 10px;
        }}
        header .subtitle {{ color: var(--text-dim); font-size: 1.1em; }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
        }}
        .card {{
            background: var(--card-bg);
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }}
        .card h2 {{
            color: var(--accent);
            margin-bottom: 15px;
            font-size: 1.3em;
            border-bottom: 1px solid #333;
            padding-bottom: 10px;
        }}
        .card.hero {{
            grid-column: 1 / -1;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
        }}
        .stat {{
            text-align: center;
            padding: 15px;
        }}
        .stat-value {{
            font-size: 2em;
            font-weight: bold;
            color: var(--accent);
        }}
        .stat-label {{ color: var(--text-dim); font-size: 0.9em; }}
        table {{ width: 100%; border-collapse: collapse; }}
        td, th {{
            padding: 8px 12px;
            text-align: left;
            border-bottom: 1px solid #333;
        }}
        th {{ color: var(--text-dim); font-weight: normal; }}
        tr:last-child td {{ border-bottom: none; }}
        .badge {{
            display: inline-block;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 0.85em;
            margin: 2px;
        }}
        .badge-success {{ background: var(--success); color: #000; }}
        .badge-warning {{ background: var(--warning); color: #000; }}
        .badge-dim {{ background: #444; color: var(--text-dim); }}
        .battery-bar {{
            height: 24px;
            background: #333;
            border-radius: 12px;
            overflow: hidden;
            margin-bottom: 15px;
        }}
        .battery-level {{
            height: 100%;
            transition: width 0.3s;
        }}
        .progress-bar {{
            height: 8px;
            background: #333;
            border-radius: 4px;
            overflow: hidden;
            margin-top: 5px;
        }}
        .progress-fill {{ height: 100%; background: var(--accent); }}
        footer {{
            text-align: center;
            padding: 30px;
            color: var(--text-dim);
            font-size: 0.9em;
        }}
        @media (max-width: 600px) {{
            .grid {{ grid-template-columns: 1fr; }}
            header h1 {{ font-size: 1.8em; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🍓 {pi_model}</h1>
            <div class="subtitle">{hostname} • Last updated: {timestamp[:19].replace('T', ' ')}</div>
        </header>

        <div class="grid">
            <!-- Hero Stats -->
            <div class="card hero">
                <div class="stat">
                    <div class="stat-value">{cpu.get('cores_logical', 'N/A')}</div>
                    <div class="stat-label">CPU Cores</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{mem.get('total_mb', 'N/A')} MB</div>
                    <div class="stat-label">RAM ({mem.get('percent_used', 0)}% used)</div>
                    <div class="progress-bar"><div class="progress-fill" style="width: {mem.get('percent_used', 0)}%"></div></div>
                </div>
                <div class="stat">
                    <div class="stat-value">{root_storage.get('total_gb', 'N/A')} GB</div>
                    <div class="stat-label">Storage ({root_storage.get('percent_used', 0)}% used)</div>
                    <div class="progress-bar"><div class="progress-fill" style="width: {root_storage.get('percent_used', 0)}%"></div></div>
                </div>
                <div class="stat">
                    <div class="stat-value">{temp}°C</div>
                    <div class="stat-label">CPU Temperature</div>
                </div>
            </div>

            <!-- System Info -->
            <div class="card">
                <h2>💻 System</h2>
                <table>
                    <tr><td>OS</td><td>{os_info.get('pretty_name', 'Unknown')}</td></tr>
                    <tr><td>Kernel</td><td>{os_info.get('kernel', {}).get('version', 'Unknown')}</td></tr>
                    <tr><td>Architecture</td><td>{cpu.get('architecture', 'Unknown')}</td></tr>
                    <tr><td>Uptime</td><td>{os_info.get('uptime', 'Unknown')}</td></tr>
                </table>
            </div>

            <!-- Network -->
            <div class="card">
                <h2>🌐 Network</h2>
                <table>
                    <tr><td>Hostname</td><td>{network.get('hostname', 'Unknown')}</td></tr>
                    {''.join(f"<tr><td>IP</td><td>{ip}</td></tr>" for ip in ip_addresses)}
                    <tr><td>Gateway</td><td>{network.get('default_gateway', 'N/A').split()[2] if network.get('default_gateway') and len(network.get('default_gateway', '').split()) > 2 else 'N/A'}</td></tr>
                    <tr><td>Open Ports</td><td>{', '.join(str(p.get('port')) for p in network.get('listening_ports', [])[:5])}</td></tr>
                </table>
            </div>

            {battery_html}
            {camera_html}
            {audio_html}
            {usb_html}

            <!-- GPIO -->
            <div class="card">
                <h2>📍 GPIO</h2>
                <p style="margin-bottom: 10px;">Available Libraries:</p>
                {''.join(f'<span class="badge badge-success">{lib}</span>' for lib in gpio_libs) or '<span class="badge badge-dim">None detected</span>'}
            </div>

            <!-- Services -->
            <div class="card">
                <h2>⚙️ Services</h2>
                <p style="margin-bottom: 10px; color: var(--text-dim);">Active:</p>
                {''.join(f'<span class="badge badge-success">{s}</span>' for s in active_services)}
            </div>

            <!-- Packages -->
            <div class="card">
                <h2>📦 Notable Packages</h2>
                <table>
                    {pkg_rows}
                </table>
            </div>
        </div>

        <footer>
            <p>Generated by Pi Discovery Script v1.0.0</p>
            <p>Run <code>~/pi_discovery/refresh.sh</code> to update</p>
        </footer>
    </div>
</body>
</html>
'''
    
    with open(output_path, 'w') as f:
        f.write(html)
    
    return output_path


def main():
    """Main function to run discovery and save results."""
    script_dir = Path(__file__).parent
    output_file = script_dir / "pi_env.json"
    html_file = script_dir / "pi_env.html"
    
    print("=" * 60)
    print("Raspberry Pi Environment Discovery")
    print("=" * 60)
    
    # Collect all info
    discovery = collect_all()
    
    # Save to JSON
    with open(output_file, "w") as f:
        json.dump(discovery, f, indent=2, default=str)
    
    # Generate HTML report
    generate_html_report(discovery, html_file)
    
    print(f"\nDiscovery complete!")
    print(f"Results saved to: {output_file}")
    print(f"HTML report: {html_file}")
    print(f"Timestamp: {discovery['meta']['discovery_timestamp']}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    pi_model = discovery['hardware']['pi_model'].get('model', 'Unknown')
    print(f"Model: {pi_model}")
    
    cpu = discovery['hardware']['cpu']
    print(f"CPU: {cpu.get('model', cpu.get('hardware', 'Unknown'))}")
    print(f"Cores: {cpu.get('cores_logical', 'Unknown')}")
    
    mem = discovery['hardware']['memory']['ram']
    print(f"RAM: {mem['total_mb']} MB ({mem['percent_used']}% used)")
    
    storage = discovery['hardware']['storage']['partitions']
    if storage:
        root = next((p for p in storage if p['mountpoint'] == '/'), storage[0])
        print(f"Storage: {root['total_gb']} GB ({root['percent_used']}% used)")
    
    temp = discovery['hardware']['temperature_voltage']['temperatures'].get('cpu_celsius')
    if temp:
        print(f"Temperature: {temp}°C")
    
    print(f"\nOS: {discovery['software']['os'].get('pretty_name', 'Unknown')}")
    print(f"Kernel: {discovery['software']['os']['kernel'].get('version', 'Unknown')}")
    print(f"Python: {discovery['software']['packages']['notable_packages'].get('python3', 'Not found')}")
    
    # Network
    net = discovery['network']
    print(f"\nHostname: {net['hostname']}")
    for iface, info in net['interfaces'].items():
        for addr in info['addresses']:
            if 'AF_INET' in addr['family'] and not addr['address'].startswith('127.'):
                print(f"IP ({iface}): {addr['address']}")
    
    wifi = discovery['peripherals']['wifi']
    if wifi.get('connected_network'):
        print(f"WiFi: {wifi['connected_network']}")
    
    # Peripherals
    usb_count = len(discovery['peripherals']['usb']['devices'])
    print(f"\nUSB Devices: {usb_count}")
    
    if discovery['peripherals']['camera']['detected']:
        print("Camera: Detected")
    
    if discovery['peripherals']['hats_addons']['detected']:
        hat = discovery['peripherals']['hats_addons']['info'].get('product', 'Unknown')
        print(f"HAT: {hat}")
    
    print("\n" + "=" * 60)
    print("Ready for hobby projects!")
    print("=" * 60)
    
    return discovery


if __name__ == "__main__":
    main()
