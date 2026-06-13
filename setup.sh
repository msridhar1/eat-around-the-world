#!/bin/bash
# setup.sh — one-time setup for Eat Around the World
# Run: bash setup.sh

echo "🌍 Eat Around the World — Setup"
echo "================================"

# Check Python
if ! command -v python3 &>/dev/null; then
  echo "✗ Python 3 not found. Install from https://python.org"
  exit 1
fi

echo "✓ Python $(python3 --version)"

# Install dependencies
echo ""
echo "Installing Python packages..."
pip3 install flask playwright 2>&1 | tail -5

echo ""
echo "Installing Playwright browsers (Chromium)..."
python3 -m playwright install chromium

echo ""
echo "✓ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Run:  bash run.sh"
echo "  2. Open: http://localhost:5050"
echo "  3. Click '↻ Sync Beli' to scrape your restaurants"
echo "  4. Or click '+ Add Restaurant' to add manually"
