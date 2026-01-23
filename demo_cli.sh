#!/bin/bash
#
# Demo: SPICE Translator CLI with Real Files
# 
# This script demonstrates the complete translation workflow using
# real Spectre model files from the repository.

set -e  # Exit on error

echo "========================================"
echo "SPICE Translator CLI Demo"
echo "========================================"
echo ""

# Setup
PROJECT_ROOT="/home/shennilee/newproject2026/proj1/new-spice-translator"
TEST_FILE="$PROJECT_ROOT/tools/spice-libraries/private-models/cadence90/spectre/gpdk090_capacitor.scs"
OUTPUT_DIR="$PROJECT_ROOT/demo_output"

mkdir -p "$OUTPUT_DIR"
cd "$PROJECT_ROOT"

echo "Using test file: $(basename $TEST_FILE)"
echo "File size: $(du -h $TEST_FILE | cut -f1)"
echo ""

# Demo 1: Get file information
echo "=== Demo 1: File Information ==="
python -m src.main info "$TEST_FILE" --format spectre
echo ""

# Demo 2: Translate Spectre → ngspice
echo "=== Demo 2: Translate Spectre → ngspice ==="
python -m src.main translate \
    "$TEST_FILE" \
    "$OUTPUT_DIR/capacitor.lib" \
    --from spectre \
    --to ngspice \
    --verbose
echo ""

# Demo 3: Validate generated file
echo "=== Demo 3: Validate ngspice Output ==="
python -m src.main validate \
    "$OUTPUT_DIR/capacitor.lib" \
    --format ngspice
echo ""

# Demo 4: Show output content
echo "=== Demo 4: Generated ngspice Content ==="
echo "First 30 lines of $OUTPUT_DIR/capacitor.lib:"
head -30 "$OUTPUT_DIR/capacitor.lib"
echo ""

# Demo 5: Translate to HSPICE
echo "=== Demo 5: Translate Spectre → HSPICE ==="
python -m src.main translate \
    "$TEST_FILE" \
    "$OUTPUT_DIR/capacitor.hsp" \
    --from spectre \
    --to hspice
echo ""

# Summary
echo "========================================"
echo "Demo Complete!"
echo "========================================"
echo ""
echo "Generated files:"
ls -lh "$OUTPUT_DIR"
echo ""
echo "To clean up: rm -rf $OUTPUT_DIR"
