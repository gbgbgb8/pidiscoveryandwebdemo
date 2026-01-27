#!/bin/bash
# Pi Control Center - Startup Script
cd "$(dirname "$0")"

echo "=============================================="
echo "  Pi Control Center"
echo "=============================================="
echo ""
echo "Starting server..."
echo "Access at: http://pi.local:5000"
echo "         or http://$(hostname -I | awk '{print $1}'):5000"
echo ""
echo "Press Ctrl+C to stop"
echo ""

python3 server.py
