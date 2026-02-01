#!/bin/bash
# Quick demo script for SPICE Translator

set -e  # Exit on error

echo "═══════════════════════════════════════"
echo "  SPICE Translator - Quick Demo"
echo "═══════════════════════════════════════"
echo ""

# Check if virtual environment is activated
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "❌ Error: Virtual environment not activated"
    echo "Please run: source .venv/bin/activate"
    exit 1
fi

# Find a sample SPICE file
SAMPLE_FILE=$(find tools/spice-libraries/private-models -name "*.scs" -type f | head -1)

if [[ -z "$SAMPLE_FILE" ]]; then
    echo "❌ Error: No sample SPICE files found"
    exit 1
fi

echo "📄 Using sample file: $SAMPLE_FILE"
echo ""

# Demo 1: Translation
echo "─────────────────────────────────────"
echo "Demo 1: Basic Translation"
echo "─────────────────────────────────────"
echo ""
echo "Command: ./cli.py translate $SAMPLE_FILE --target ngspice"
echo ""

./cli.py translate "$SAMPLE_FILE" --target ngspice

echo ""
echo "✅ Translation complete!"
echo ""

# Demo 2: List available models (if gpdk090 exists)
GPDK_FILE="tools/spice-libraries/private-models/gpdk090/gpdk090.scs"

if [[ -f "$GPDK_FILE" ]]; then
    echo "─────────────────────────────────────"
    echo "Demo 2: List Models in gpdk090.scs"
    echo "─────────────────────────────────────"
    echo ""
    
    echo "Available capacitor models:"
    grep "^model.*capacitor" "$GPDK_FILE" | head -3 || echo "  (none found)"
    echo ""
    
    echo "Available MOS models:"
    grep "^model.*bsim" "$GPDK_FILE" | head -3 || echo "  (none found)"
    echo ""
fi

# Demo 3: Show output structure
echo "─────────────────────────────────────"
echo "Demo 3: Output File Structure"
echo "─────────────────────────────────────"
echo ""

if [[ -d "output" ]]; then
    echo "output/"
    ls -lh output/ 2>/dev/null || true
    echo ""
    
    # Show a sample translated file (first 20 lines)
    SAMPLE_OUTPUT=$(find output -name "*.lib" -o -name "*.cir" | head -1)
    if [[ -n "$SAMPLE_OUTPUT" ]]; then
        echo "Sample output ($SAMPLE_OUTPUT - first 20 lines):"
        echo "─────────────────────────────────────"
        head -20 "$SAMPLE_OUTPUT"
        echo "─────────────────────────────────────"
    fi
fi

echo ""
echo "═══════════════════════════════════════"
echo "  Demo Complete!"
echo "═══════════════════════════════════════"
echo ""
echo "Next steps:"
echo "  1. Read USAGE_GUIDE.md for complete examples"
echo "  2. Try verification: ./cli.py verify --help"
echo "  3. Run regression: ./cli.py verify-all --target ngspice"
echo ""
