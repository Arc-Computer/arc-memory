#!/bin/bash
# Script to build and publish the package to PyPI

# Ensure we're in the project root
cd "$(dirname "$0")/.."

# Clean up previous builds
rm -rf dist/ build/ *.egg-info/

# Build the package
echo "Building package..."
python -m build

# Upload to PyPI
echo "Uploading to PyPI..."
python -m twine upload dist/*

echo "Done!"
