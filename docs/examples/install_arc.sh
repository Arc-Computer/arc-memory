#!/bin/bash
# Arc Memory Installation Script
# Usage: curl -sSL https://arc.computer/install.sh | bash
# Or: curl -sSL https://arc.computer/install.sh | bash -s -- --with-github --with-linear

set -e

# Default options
INSTALL_GITHUB=false
INSTALL_LINEAR=false
INSTALL_LLM=false
INSTALL_ALL=false
PYTHON_CMD=""

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --with-github) INSTALL_GITHUB=true ;;
        --with-linear) INSTALL_LINEAR=true ;;
        --with-llm) INSTALL_LLM=true ;;
        --all) INSTALL_ALL=true ;;
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
echo "Arc Memory Installation Script"
echo "============================="
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

# Check Python version
PYTHON_VERSION=$($PYTHON_CMD -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PYTHON_VERSION_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_VERSION_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_VERSION_MAJOR" -lt 3 ] || ([ "$PYTHON_VERSION_MAJOR" -eq 3 ] && [ "$PYTHON_VERSION_MINOR" -lt 10 ]); then
    echo "Error: Arc Memory requires Python 3.10 or higher. Found Python $PYTHON_VERSION."
    exit 1
fi

echo "Using Python $PYTHON_VERSION"

# Determine installation options
if [ "$INSTALL_ALL" = true ]; then
    INSTALL_OPTS="[all]"
    echo "Installing Arc Memory with all dependencies..."
else
    INSTALL_OPTS=""
    if [ "$INSTALL_GITHUB" = true ]; then
        INSTALL_OPTS="${INSTALL_OPTS}github,"
    fi
    if [ "$INSTALL_LINEAR" = true ]; then
        INSTALL_OPTS="${INSTALL_OPTS}linear,"
    fi
    if [ "$INSTALL_LLM" = true ]; then
        INSTALL_OPTS="${INSTALL_OPTS}llm,"
    fi
    
    # Remove trailing comma if present
    INSTALL_OPTS=${INSTALL_OPTS%,}
    
    if [ -n "$INSTALL_OPTS" ]; then
        INSTALL_OPTS="[$INSTALL_OPTS]"
        echo "Installing Arc Memory with options: $INSTALL_OPTS"
    else
        echo "Installing Arc Memory with basic dependencies..."
    fi
fi

# Install Arc Memory
echo "Installing Arc Memory..."
$PYTHON_CMD -m pip install --upgrade pip
$PYTHON_CMD -m pip install "arc-memory$INSTALL_OPTS"

# Verify installation
if $PYTHON_CMD -c "import arc_memory; print(f'Arc Memory {arc_memory.__version__} installed successfully!')" &>/dev/null; then
    VERSION=$($PYTHON_CMD -c "import arc_memory; print(arc_memory.__version__)")
    echo "✅ Arc Memory $VERSION installed successfully!"
else
    echo "❌ Installation failed. Please check the error messages above."
    exit 1
fi

# Check for Ollama if LLM enhancement is requested
if [ "$INSTALL_LLM" = true ] || [ "$INSTALL_ALL" = true ]; then
    echo "Checking for Ollama..."
    if command -v ollama &>/dev/null; then
        echo "✅ Ollama is installed."
    else
        echo "⚠️ Ollama is not installed. LLM enhancement requires Ollama."
        echo "Install Ollama from: https://ollama.ai/download"
        echo "After installing, run: ollama pull gemma3:27b-it-qat"
    fi
fi

# Setup instructions
echo ""
echo "Next Steps:"
echo "1. Navigate to your repository:"
echo "   cd /path/to/your/repo"
echo ""
echo "2. Build your knowledge graph:"
echo "   arc build"
echo ""
if [ "$INSTALL_GITHUB" = true ] || [ "$INSTALL_ALL" = true ]; then
    echo "3. Authenticate with GitHub:"
    echo "   arc auth github"
    echo ""
fi
if [ "$INSTALL_LINEAR" = true ] || [ "$INSTALL_ALL" = true ]; then
    echo "4. Authenticate with Linear:"
    echo "   arc auth linear"
    echo ""
fi
if [ "$INSTALL_LLM" = true ] || [ "$INSTALL_ALL" = true ]; then
    echo "5. Build with LLM enhancement:"
    echo "   arc build --llm-enhancement"
    echo ""
fi
echo "For more information, visit: https://github.com/Arc-Computer/arc-memory"
echo ""
