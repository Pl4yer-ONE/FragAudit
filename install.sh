#!/bin/bash
# FragAudit Quick Install Script
# Usage: curl -sSL https://raw.githubusercontent.com/Pl4yer-ONE/FragAudit/main/install.sh | bash

set -e

echo "╔═══════════════════════════════════════╗"
echo "║       FragAudit Installer             ║"
echo "║   CS2 Performance Verification        ║"
echo "╚═══════════════════════════════════════╝"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Install Python 3.10+ first."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "✓ Python $PYTHON_VERSION detected"

# Clone or update
if [ -d "FragAudit" ]; then
    echo "→ Updating existing installation..."
    cd FragAudit
    git pull origin main
else
    echo "→ Cloning FragAudit..."
    git clone https://github.com/Pl4yer-ONE/FragAudit.git
    cd FragAudit
fi

# Virtual environment
if [ ! -d "venv" ]; then
    echo "→ Creating virtual environment..."
    python3 -m venv venv
fi

echo "→ Activating virtual environment..."
source venv/bin/activate

echo "→ Installing dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

echo ""
echo "╔═══════════════════════════════════════╗"
echo "║         Installation Complete         ║"
echo "╚═══════════════════════════════════════╝"
echo ""
echo "Usage:"
echo "  cd FragAudit"
echo "  source venv/bin/activate"
echo ""
echo "  # Play a demo"
echo "  python main.py play match/demo.dem"
echo ""
echo "  # Analyze a demo"
echo "  python main.py analyze --demo match/demo.dem"
echo ""
echo "  # Run tests"
echo "  python -m pytest tests/ -v"
echo ""
