# 1. Copy zip to new Pi
scp -v ./pi_discovery_v1.0.0_dist.zip pi@newpi.local:

# 2. SSH to new Pi and extract
ssh pi@newpi.local
unzip pi_discovery_v1.0.0_dist.zip
cd pi_discovery

# 3. Install dependencies
sudo apt update
sudo apt install -y python3-psutil python3-flask espeak-ng alsa-utils rpicam-apps i2c-tools

# 4. Make scripts executable
chmod +x *.sh demo/*.sh demo/*.py

# 5. Run discovery to generate fresh data for this Pi
python3 discover.py

# 6. Start the control center
cd demo && python3 server.py

# 7. (Optional) Enable autostart
sudo cp /dev/stdin /etc/systemd/system/pi-control-center.service << 'EOF'
[Unit]
Description=Pi Control Center Web Server
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/pi_discovery/demo
ExecStart=/usr/bin/python3 /home/pi/pi_discovery/demo/server.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl enable --now pi-control-center
