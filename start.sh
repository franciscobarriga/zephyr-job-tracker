#!/bin/bash
# Zephyr Startup Script

cd "$(dirname "$0")"

echo "🌪️  Starting Zephyr Server"
echo "======================================"
echo ""

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "❌ venv not found. Creating it now..."
    python3 -m venv venv
    ./venv/bin/pip install --upgrade pip
    ./venv/bin/pip install -r requirements.txt
fi

# Start the server
./venv/bin/python run.py
