#!/bin/bash
# Startup script for Digital Twin Backend
# This script activates the virtual environment and starts the server

cd "$(dirname "$0")"

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "❌ Virtual environment not found. Please run setup first."
    exit 1
fi

# Set PYTHONPATH to include current directory
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Start the server
echo "🚀 Starting Digital Twin Backend..."
python main.py

