#!/bin/bash
# run.sh — start the Eat Around the World dashboard
# Run: bash run.sh

echo "🌍 Starting Eat Around the World..."

# Get local IP for sharing
LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}')

echo ""
echo "Dashboard will be at:"
echo "  You:         http://localhost:5050"
if [ -n "$LOCAL_IP" ]; then
  echo "  Your bf:     http://$LOCAL_IP:5050  (must be on same WiFi)"
fi
echo ""
echo "Press Ctrl+C to stop."
echo ""

python3 app.py
