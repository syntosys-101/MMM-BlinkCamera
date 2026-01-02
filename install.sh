#!/bin/bash
# MMM-BlinkCamera Installation

echo ""
echo "================================"
echo "  MMM-BlinkCamera Installation"
echo "================================"
echo ""

# Check we're in the right place
if [ ! -f "MMM-BlinkCamera.js" ]; then
    echo "Error: Run this from the MMM-BlinkCamera directory"
    exit 1
fi

# Check Python
echo "Checking Python..."
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 not found"
    echo "Install: sudo apt install python3 python3-pip"
    exit 1
fi
echo "✓ Python3: $(python3 --version)"

# Install dependencies
echo ""
echo "Installing Python packages..."
pip3 install -r python/requirements.txt --break-system-packages 2>/dev/null || \
pip3 install -r python/requirements.txt --user 2>/dev/null || \
pip3 install -r python/requirements.txt

# Verify
echo ""
echo "Verifying..."
if python3 -c "import blinkpy, aiohttp, aiofiles" 2>/dev/null; then
    echo "✓ Dependencies installed"
else
    echo "✗ Some packages may be missing"
    echo "  Try: pip3 install blinkpy aiohttp aiofiles"
fi

# Make executable
chmod +x python/*.py 2>/dev/null

echo ""
echo "================================"
echo "  Installation Complete!"
echo "================================"
echo ""
echo "Next steps:"
echo ""
echo "1. Authenticate with Blink:"
echo "   python3 python/setup_auth.py"
echo ""
echo "2. Add to config/config.js:"
echo "   {"
echo "     module: \"MMM-BlinkCamera\","
echo "     position: \"middle_center\","
echo "     config: {"
echo "       email: \"your@email.com\","
echo "       password: \"your-password\""
echo "     }"
echo "   }"
echo ""
echo "3. Restart MagicMirror"
echo ""
