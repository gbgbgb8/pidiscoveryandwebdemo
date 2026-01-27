#!/bin/bash
# Serve the Pi Discovery web page
# Access at http://pi.local:8080 or http://<pi-ip>:8080

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT=${1:-8080}

echo "=============================================="
echo "  Pi Discovery Web Server"
echo "=============================================="
echo ""
echo "Serving files from: $SCRIPT_DIR"
echo ""
echo "Access the dashboard at:"
echo "  http://$(hostname).local:$PORT/pi_env.html"
echo "  http://$(hostname -I | awk '{print $1}'):$PORT/pi_env.html"
echo ""
echo "Press Ctrl+C to stop"
echo ""

cd "$SCRIPT_DIR"
python3 -m http.server $PORT
