#!/bin/bash
# Setup script for JogaJunto Listing Generator

set -e

echo "Creating virtual environment..."
python3 -m venv venv

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "Setup complete! To use the script:"
echo "  source venv/bin/activate"
echo "  python generate_listing.py"
echo ""
echo "Or run directly:"
echo "  ./run.sh"

