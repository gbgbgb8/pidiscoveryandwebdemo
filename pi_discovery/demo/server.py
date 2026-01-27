#!/usr/bin/env python3
"""Pi Control Center - Flask Backend"""
import json, subprocess, socket, re
from pathlib import Path
from datetime import datetime
from flask import Flask, jsonify, request, send_file, Response, send_from_directory

app = Flask(__name__, static_folder='static')
PI_DIR = Path(__file__).parent.parent
DEMO_DIR = Path(__file__).parent
CONFIG_FILE = DEMO_DIR / 'config.json'

def load_config():
    """Load settings from config file."""
    defaults = {"announcement_enabled": True, "autostart_enabled": True}
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE) as f:
                cfg = json.load(f)
                defaults.update(cfg)
    except:
        pass
    return defaults

def save_config(cfg):
    """Save settings to config file."""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(cfg, f, indent=2)
        return True
    except:
        return False

def run_cmd(cmd, shell=False, timeout=10):
    try:
        r = subprocess.run(cmd, shell=shell, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip(), r.stderr.strip(), r.returncode
    except:
        return None, "error", 1

def pisugar(cmd):
    try:
        s = socket.socket()
        s.settimeout(2)
        s.connect(("127.0.0.1", 8423))
        s.send((cmd + "\n").encode())
        r = s.recv(1024).decode().strip()
        s.close()
        return r.split(": ", 1)[1] if ": " in r else r
    except:
        return None

@app.route('/')
def index():
    return send_file(DEMO_DIR / 'index.html')

@app.route('/static/<path:f>')
def static_files(f):
    return send_from_directory(DEMO_DIR / 'static', f)

@app.route('/dashboard')
def dashboard():
    return send_file(PI_DIR / 'pi_env.html')

@app.route('/api/stats')
def stats():
    import psutil
    temp = None
    out, _, _ = run_cmd(["vcgencmd", "measure_temp"])
    if out:
        m = re.search(r"temp=(\d+\.?\d*)", out)
        if m: temp = float(m.group(1))
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    bat = pisugar("get battery")
    bat_val = None
    if bat:
        try:
            bat_val = float(bat)
        except (ValueError, TypeError):
            bat_val = None
    return jsonify({
        'temperature': round(temp, 1) if temp else None,
        'ram_percent': mem.percent,
        'disk_percent': disk.percent,
        'battery': bat_val
    })

@app.route('/api/info')
def info():
    model = os_name = "Unknown"
    try:
        with open('/proc/device-tree/model') as f:
            model = f.read().replace('\x00', '').strip()
    except: pass
    try:
        for l in open('/etc/os-release'):
            if l.startswith('PRETTY_NAME='):
                os_name = l.split('=')[1].strip().strip('"')
                break
    except: pass
    out, _, _ = run_cmd(["hostname", "-I"])
    ip = out.split()[0] if out else "?"
    out2, _, _ = run_cmd(["uptime", "-p"])
    return jsonify({
        'hostname': socket.gethostname(),
        'model': model, 'os': os_name,
        'ip': ip, 'uptime': out2 or "?"
    })

@app.route('/api/discovery')
def discovery():
    with open(PI_DIR / 'pi_env.json') as f:
        return jsonify(json.load(f))

@app.route('/api/discovery/run', methods=['POST'])
def run_discovery():
    _, _, code = run_cmd(["python3", str(PI_DIR / "discover.py")], timeout=60)
    return jsonify({'success': code == 0})

@app.route('/api/camera/stream')
def cam_stream():
    def gen():
        cmd = ['rpicam-vid','-t','0','--inline','--width','640',
               '--height','480','--framerate','15','--codec','mjpeg','-o','-']
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        buf = b''
        try:
            while True:
                c = p.stdout.read(4096)
                if not c: break
                buf += c
                s, e = buf.find(b'\xff\xd8'), buf.find(b'\xff\xd9')
                if s != -1 and e != -1 and e > s:
                    yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buf[s:e+2] + b'\r\n'
                    buf = buf[e+2:]
        finally: p.terminate()
    return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/camera/photo')
def cam_photo():
    path = DEMO_DIR / f'photo_{datetime.now().strftime("%H%M%S")}.jpg'
    _, err, code = run_cmd(['rpicam-still','-o',str(path),'--width','1920','--height','1080','-t','1000'], timeout=10)
    return send_file(path, mimetype='image/jpeg') if code == 0 else (jsonify({'error': err}), 500)

@app.route('/api/audio/record')
def audio_rec():
    dur = min(request.args.get('duration', 5, type=int), 30)
    path = DEMO_DIR / f'rec_{datetime.now().strftime("%H%M%S")}.wav'
    _, err, code = run_cmd(['arecord','-D','plughw:1,0','-f','S16_LE','-r','44100','-c','1','-d',str(dur),str(path)], timeout=dur+5)
    return send_file(path, mimetype='audio/wav') if code == 0 else (jsonify({'error': err}), 500)

@app.route('/api/audio/speak', methods=['POST'])
def audio_speak():
    text = request.get_json().get('text', '')[:200]
    if not text: return jsonify({'error': 'No text'}), 400
    p = subprocess.Popen(['espeak-ng','--stdout',text], stdout=subprocess.PIPE)
    subprocess.run(['aplay','-D','plughw:0,0'], stdin=p.stdout, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return jsonify({'success': True})

@app.route('/api/audio/sound/<s>', methods=['POST'])
def audio_sound(s):
    f = {'beep': 800, 'chime': 1200, 'alert': 400}.get(s)
    if not f: return jsonify({'error': 'Unknown'}), 400
    subprocess.Popen(['speaker-test','-D','plughw:0,0','-t','sine','-f',str(f),'-l','1'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return jsonify({'success': True})

@app.route('/api/audio/volume', methods=['POST'])
def audio_vol():
    v = max(0, min(100, request.get_json().get('volume', 50)))
    run_cmd(['amixer','-c','0','set','PCM',f'{v}%'])
    return jsonify({'success': True})

@app.route("/api/audio/levels")
def audio_levels():
    import struct
    try:
        proc = subprocess.run(["arecord", "-D", "plughw:1,0", "-f", "S16_LE", "-r", "8000", "-c", "1", "-d", "1", "-q", "-t", "raw"], capture_output=True, timeout=3)
        if proc.returncode != 0 or len(proc.stdout) < 100: return jsonify({"level": 0})
        samples = struct.unpack(f"<{len(proc.stdout)//2}h", proc.stdout)
        rms = (sum(s*s for s in samples) / len(samples)) ** 0.5
        level = min(100, int((rms / 3276.7) * 100))
        return jsonify({"level": level})
    except: return jsonify({"level": 0})

gpio_state = {17: False, 27: False, 22: False, 23: False}

@app.route('/api/gpio/set', methods=['POST'])
def gpio_set():
    d = request.get_json()
    pin, state = d.get('pin'), d.get('state', False)
    if pin not in gpio_state: return jsonify({'error': 'Bad pin'}), 400
    gpio_state[pin] = state
    return jsonify({'success': True, 'pin': pin, 'state': state})

@app.route('/api/gpio/blink', methods=['POST'])
def gpio_blink():
    return jsonify({'success': True})

@app.route('/api/gpio/off', methods=['POST'])
def gpio_off():
    for p in gpio_state: gpio_state[p] = False
    return jsonify({'success': True})

@app.route('/api/terminal/run', methods=['POST'])
def terminal():
    cmd = request.get_json().get('command', '').strip()
    allowed = ['ls','pwd','date','uptime','df','free','echo','hostname','uname','vcgencmd']
    if not cmd or cmd.split()[0] not in allowed:
        return jsonify({'error': 'Not allowed'}), 403
    out, err, code = run_cmd(cmd, shell=True, timeout=10)
    return jsonify({'output': out, 'error': err if code else None})

@app.route('/api/battery')
def battery():
    def safe_float(val):
        try:
            return float(val) if val else 0
        except (ValueError, TypeError):
            return 0
    return jsonify({
        'percent': safe_float(pisugar("get battery")),
        'voltage': safe_float(pisugar("get battery_v"))
    })

# === FILE BROWSER ===
import shutil
BLOCKED_PATHS = ['/etc/shadow', '/etc/passwd', '/etc/sudoers']

def is_safe(path, write=False):
    try:
        r = Path(path).resolve()
        if write:
            for b in BLOCKED_PATHS:
                if str(r).startswith(b): return False
        return True
    except: return False

@app.route('/api/files/list')
def files_list():
    path = request.args.get('path', '/home/pi')
    try:
        p = Path(path).resolve()
        if not p.exists(): return jsonify({'error': 'Not found'}), 404
        if not p.is_dir(): return jsonify({'error': 'Not a dir'}), 400
        items = []
        for item in sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            try:
                st = item.stat()
                items.append({'name': item.name, 'path': str(item), 'is_dir': item.is_dir(),
                    'size': st.st_size if item.is_file() else None,
                    'modified': datetime.fromtimestamp(st.st_mtime).isoformat()})
            except: items.append({'name': item.name, 'path': str(item), 'is_dir': item.is_dir(), 'error': 'denied'})
        return jsonify({'path': str(p), 'parent': str(p.parent), 'items': items})
    except Exception as e: return jsonify({'error': str(e)}), 500

@app.route('/api/files/read')
def files_read():
    path = request.args.get('path', '')
    if not path: return jsonify({'error': 'No path'}), 400
    try:
        p = Path(path).resolve()
        if not p.exists() or not p.is_file(): return jsonify({'error': 'Not found'}), 404
        if p.stat().st_size > 1024*1024: return jsonify({'error': 'Too large'}), 400
        return jsonify({'path': str(p), 'content': p.read_text(errors='replace')})
    except Exception as e: return jsonify({'error': str(e)}), 500

@app.route('/api/files/download')
def files_download():
    path = request.args.get('path', '')
    try:
        p = Path(path).resolve()
        if p.exists() and p.is_file(): return send_file(p, as_attachment=True)
        return jsonify({'error': 'Not found'}), 404
    except Exception as e: return jsonify({'error': str(e)}), 500

@app.route('/api/files/upload', methods=['POST'])
def files_upload():
    path = request.form.get('path', '/home/pi')
    if not is_safe(path, True): return jsonify({'error': 'Blocked'}), 403
    if 'file' not in request.files: return jsonify({'error': 'No file'}), 400
    f = request.files['file']
    try:
        dest = Path(path).resolve() / f.filename
        f.save(str(dest))
        return jsonify({'success': True, 'path': str(dest)})
    except Exception as e: return jsonify({'error': str(e)}), 500

@app.route('/api/files/mkdir', methods=['POST'])
def files_mkdir():
    data = request.get_json()
    path = data.get('path', '')
    if not path or not is_safe(path, True): return jsonify({'error': 'Invalid'}), 400
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        return jsonify({'success': True})
    except Exception as e: return jsonify({'error': str(e)}), 500

@app.route('/api/files/delete', methods=['DELETE'])
def files_delete():
    path = request.args.get('path', '')
    if not path or not is_safe(path, True): return jsonify({'error': 'Blocked'}), 403
    try:
        p = Path(path).resolve()
        if str(p) in ['/home/pi/pi_discovery', '/home', '/etc', '/usr', '/var', '/boot']:
            return jsonify({'error': 'Protected'}), 403
        if p.is_dir(): shutil.rmtree(p)
        else: p.unlink()
        return jsonify({'success': True})
    except Exception as e: return jsonify({'error': str(e)}), 500

# === TIMELAPSE ===
TIMELAPSE_DIR = DEMO_DIR / 'timelapse'
TIMELAPSE_DIR.mkdir(exist_ok=True)
timelapse_thread = None
timelapse_stop = False

def timelapse_worker(interval, max_shots):
    global timelapse_stop
    count = 0
    while not timelapse_stop and (max_shots == 0 or count < max_shots):
        fname = TIMELAPSE_DIR / f'img_{datetime.now().strftime("%Y%m%d_%H%M%S")}.jpg'
        run_cmd(['rpicam-still', '-o', str(fname), '--width', '1280', '--height', '720', '-t', '500'], timeout=10)
        count += 1
        for _ in range(int(interval)):
            if timelapse_stop: break
            import time; time.sleep(1)

@app.route('/api/timelapse/status')
def timelapse_status():
    global timelapse_thread
    running = timelapse_thread is not None and timelapse_thread.is_alive()
    images = sorted(TIMELAPSE_DIR.glob('*.jpg'), key=lambda x: x.stat().st_mtime, reverse=True)
    return jsonify({
        'running': running,
        'count': len(images),
        'images': [{'name': i.name, 'path': str(i)} for i in images[:20]]
    })

@app.route('/api/timelapse/start', methods=['POST'])
def timelapse_start():
    global timelapse_thread, timelapse_stop
    if timelapse_thread and timelapse_thread.is_alive():
        return jsonify({'error': 'Already running'}), 400
    data = request.get_json() or {}
    interval = max(10, min(600, data.get('interval', 60)))
    duration = data.get('duration', 0)
    max_shots = int(duration / interval) if duration > 0 else 0
    timelapse_stop = False
    timelapse_thread = threading.Thread(target=timelapse_worker, args=(interval, max_shots), daemon=True)
    timelapse_thread.start()
    return jsonify({'success': True, 'interval': interval})

@app.route('/api/timelapse/stop', methods=['POST'])
def timelapse_stop_route():
    global timelapse_stop
    timelapse_stop = True
    return jsonify({'success': True})

@app.route('/api/timelapse/image/<name>')
def timelapse_image(name):
    path = TIMELAPSE_DIR / name
    if path.exists(): return send_file(path)
    return jsonify({'error': 'Not found'}), 404

@app.route('/api/timelapse/clear', methods=['DELETE'])
def timelapse_clear():
    for f in TIMELAPSE_DIR.glob('*.jpg'): f.unlink()
    return jsonify({'success': True})

# === LOG VIEWER ===
LOG_SOURCES = {
    'syslog': {'cmd': ['journalctl', '-n', '{lines}', '--no-pager']},
    'dmesg': {'cmd': ['dmesg', '--human', '-T']},
    'auth': {'cmd': ['journalctl', '-u', 'ssh', '-n', '{lines}', '--no-pager']},
    'pi-control-center': {'cmd': ['journalctl', '-u', 'pi-control-center', '-n', '{lines}', '--no-pager']},
    'kernel': {'cmd': ['journalctl', '-k', '-n', '{lines}', '--no-pager']},
}

@app.route('/api/logs/sources')
def log_sources():
    """List available log sources."""
    return jsonify({'sources': list(LOG_SOURCES.keys())})

@app.route('/api/logs/read')
def log_read():
    """Read log entries from a source."""
    source = request.args.get('source', 'syslog')
    lines = min(int(request.args.get('lines', 100)), 1000)
    
    if source not in LOG_SOURCES:
        return jsonify({'error': 'Unknown source'}), 400
    
    cmd = [c.replace('{lines}', str(lines)) for c in LOG_SOURCES[source]['cmd']]
    out, err, code = run_cmd(cmd, timeout=15)
    
    # For dmesg, take last N lines
    if source == 'dmesg' and out:
        out = '\n'.join(out.split('\n')[-lines:])
    
    return jsonify({'source': source, 'lines': lines, 'content': out or err or 'No logs available'})

@app.route('/api/power/reboot', methods=['POST'])
def power_reboot():
    """Reboot the Pi."""
    run_cmd(['sudo', 'reboot'], timeout=5)
    return jsonify({'success': True, 'message': 'Rebooting...'})

@app.route('/api/power/shutdown', methods=['POST'])
def power_shutdown():
    """Shutdown the Pi."""
    run_cmd(['sudo', 'poweroff'], timeout=5)
    return jsonify({'success': True, 'message': 'Shutting down...'})

@app.route('/api/announce', methods=['POST'])
def play_announcement():
    """Play the startup announcement now."""
    try:
        out, _, _ = run_cmd(["hostname", "-I"])
        ip = out.split()[0] if out else "pi.local"
    except:
        ip = "pi.local"
    
    message = f"Pi Control Center ready. Accessible at {ip}, port 5000."
    try:
        p = subprocess.Popen(['espeak-ng', '--stdout', message], stdout=subprocess.PIPE)
        subprocess.run(['aplay', '-D', 'plughw:0,0'], stdin=p.stdout,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
        return jsonify({'success': True, 'message': message})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/settings')
def get_settings():
    """Get current settings."""
    cfg = load_config()
    # Check actual systemd status
    out, _, code = run_cmd(['systemctl', 'is-enabled', 'pi-control-center'])
    cfg['autostart_enabled'] = (code == 0)
    return jsonify(cfg)

@app.route('/api/settings', methods=['POST'])
def update_settings():
    """Update settings."""
    data = request.get_json()
    cfg = load_config()
    
    # Update announcement setting
    if 'announcement_enabled' in data:
        cfg['announcement_enabled'] = bool(data['announcement_enabled'])
    
    # Update autostart setting
    if 'autostart_enabled' in data:
        enabled = bool(data['autostart_enabled'])
        cfg['autostart_enabled'] = enabled
        # Actually enable/disable the systemd service
        if enabled:
            run_cmd(['sudo', 'systemctl', 'enable', 'pi-control-center'])
        else:
            run_cmd(['sudo', 'systemctl', 'disable', 'pi-control-center'])
    
    save_config(cfg)
    return jsonify({'success': True, 'settings': cfg})

import threading

def announce_ready():
    """Announce when server is ready via text-to-speech."""
    import time
    time.sleep(4)  # Wait for server to be fully ready
    
    # Check if announcement is enabled
    cfg = load_config()
    if not cfg.get('announcement_enabled', True):
        return
    
    try:
        out, _, _ = run_cmd(["hostname", "-I"])
        ip = out.split()[0] if out else "pi.local"
    except:
        ip = "pi.local"
    
    message = f"Pi Control Center ready. Accessible at {ip}, port 5000."
    try:
        p = subprocess.Popen(['espeak-ng', '--stdout', message], stdout=subprocess.PIPE)
        subprocess.run(['aplay', '-D', 'plughw:0,0'], stdin=p.stdout, 
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
    except:
        pass  # Ignore if audio fails

if __name__ == '__main__':
    print("=" * 50)
    print("Pi Control Center")
    print("http://pi.local:5000")
    print("=" * 50)
    
    # Start announcement in background
    threading.Thread(target=announce_ready, daemon=True).start()
    
    app.run(host='0.0.0.0', port=5000, threaded=True)
