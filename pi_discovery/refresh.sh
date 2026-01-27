#!/bin/bash
# Refresh Pi environment discovery
# Run this script to update pi_env.json with current system state

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Refreshing Pi environment discovery..."
python3 discover.py

echo ""
echo "To view the JSON file:"
echo "  cat $SCRIPT_DIR/pi_env.json"
echo ""
echo "To view formatted JSON (if jq is installed):"
echo "  jq . $SCRIPT_DIR/pi_env.json"
