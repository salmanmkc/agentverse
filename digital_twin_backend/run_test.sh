#!/bin/bash
# Test script runner - ensures venv is used
cd "$(dirname "$0")"

if [ -d "venv" ]; then
    source venv/bin/activate
    export PYTHONPATH="$(pwd):$PYTHONPATH"
    echo "✅ Using venv Python: $(which python)"
    python test_pipeline.py "$@"
else
    echo "❌ Virtual environment not found. Please run setup first."
    exit 1
fi

