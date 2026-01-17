#!/bin/bash
# Run script for JogaJunto Listing Generator

set -e

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Running setup..."
    ./setup.sh
fi

# Activate virtual environment
source venv/bin/activate

# Run the script
python generate_listing.py

