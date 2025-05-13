#!/bin/bash
# Arc Memory Uninstallation Script
# Usage: curl -sSL https://arc.computer/uninstall.sh | bash
# Or: curl -sSL https://arc.computer/uninstall.sh | bash -s -- --remove-data

set -e

# Default options
REMOVE_DATA=false
PYTHON_CMD=""

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --remove-data) REMOVE_DATA=true ;;
        --python) PYTHON_CMD="$2"; shift ;;
        *) echo "Unknown parameter: $1"; exit 1 ;;
    esac
    shift
done

# ASCII art banner
echo "
   _____                __  __                                 
  / ____|              |  \/  |                                
 | (___   ___ _ __ ___ | \  / | ___ _ __ ___   ___  _ __ _   _ 
  \___ \ / __| '__/ _ \| |\/| |/ _ \ '_ \` _ \ / _ \| '__| | | |
  ____) | (__| | | (_) | |  | |  __/ | | | | | (_) | |  | |_| |
 |_____/ \___|_|  \___/|_|  |_|\___|_| |_| |_|\___/|_|   \__, |
                                                          __/ |
                                                         |___/ 
"
echo "Arc Memory Uninstallation Script"
echo "==============================="
echo ""

# Find Python command
if [ -z "$PYTHON_CMD" ]; then
    if command -v python3 &>/dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &>/dev/null; then
        PYTHON_CMD="python"
    else
        echo "Error: Python not found. Please install Python 3.10 or higher."
        exit 1
    fi
fi

# Check if Arc Memory is installed
if ! $PYTHON_CMD -c "import arc_memory" &>/dev/null; then
    echo "Arc Memory is not installed. Nothing to uninstall."
    exit 0
fi

# Get installation information
VERSION=$($PYTHON_CMD -c "import arc_memory; print(arc_memory.__version__)")
INSTALL_PATH=$($PYTHON_CMD -c "import arc_memory; import os; print(os.path.dirname(arc_memory.__file__))")

echo "Found Arc Memory version $VERSION installed at:"
echo "$INSTALL_PATH"
echo ""

# Confirm uninstallation
read -p "Do you want to uninstall Arc Memory? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Uninstallation cancelled."
    exit 0
fi

# Uninstall Arc Memory
echo "Uninstalling Arc Memory..."
$PYTHON_CMD -m pip uninstall -y arc-memory

# Verify uninstallation
if ! $PYTHON_CMD -c "import arc_memory" &>/dev/null; then
    echo "✅ Arc Memory has been successfully uninstalled."
else
    echo "❌ Failed to uninstall Arc Memory. Please try manually with 'pip uninstall arc-memory'."
    exit 1
fi

# Handle data removal
if [ "$REMOVE_DATA" = true ]; then
    echo "Removing Arc Memory data..."
    
    # Remove .arc directory
    ARC_DIR="$HOME/.arc"
    if [ -d "$ARC_DIR" ]; then
        echo "Removing $ARC_DIR..."
        rm -rf "$ARC_DIR"
        echo "✅ Removed Arc Memory data directory."
    else
        echo "No Arc Memory data directory found at $ARC_DIR."
    fi
    
    # Remove keyring entries
    echo "Removing authentication tokens from keyring..."
    $PYTHON_CMD -c "
import sys
try:
    import keyring
    keyring.delete_password('arc_memory', 'github_token')
    keyring.delete_password('arc_memory', 'linear_token')
    print('✅ Removed authentication tokens from keyring.')
except Exception as e:
    print(f'Failed to remove keyring entries: {e}')
    sys.exit(0)
"
else
    echo ""
    echo "Note: Arc Memory data has been preserved. To remove all data, run:"
    echo "curl -sSL https://arc.computer/uninstall.sh | bash -s -- --remove-data"
    echo ""
    echo "Or manually remove the following:"
    echo "- Data directory: $HOME/.arc"
    echo "- Authentication tokens in your system keyring"
fi

echo ""
echo "Thank you for trying Arc Memory! We'd love to hear your feedback."
echo "Please visit https://github.com/Arc-Computer/arc-memory/issues to share your experience."
echo ""
