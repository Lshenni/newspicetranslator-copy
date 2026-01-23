#!/bin/bash
# Test lowering for all three backends
set -e

echo "🔬 MULTI-BACKEND LOWERING TEST"
echo "=============================="
echo ""

INPUT_FILE="tools/spice-libraries/private-models/cadence90/spectre/gpdk090_capacitor.scs"

# Test ngspice
echo "1️⃣ Testing ngspice lowering..."
python -c "
from src.main import TranslationEngine
from pathlib import Path

engine = TranslationEngine()
result = engine.translate(
    input_file=Path('$INPUT_FILE'),
    output_file=Path('output/spectre_to_ngspice/gpdk090_capacitor.lib'),
    source_format='spectre',
    target_format='ngspice',
    validate=False
)
print(f'✅ ngspice: {result[\"models_translated\"]} models' if result['success'] else f'❌ ngspice failed')
"

# Test HSPICE
echo ""
echo "2️⃣ Testing HSPICE lowering..."
python -c "
from src.main import TranslationEngine
from pathlib import Path

engine = TranslationEngine()
result = engine.translate(
    input_file=Path('$INPUT_FILE'),
    output_file=Path('output/spectre_to_hspice/gpdk090_capacitor.sp'),
    source_format='spectre',
    target_format='hspice',
    validate=False
)
print(f'✅ HSPICE: {result[\"models_translated\"]} models' if result['success'] else f'❌ HSPICE failed')
"

# Test Spectre (roundtrip)
echo ""
echo "3️⃣ Testing Spectre roundtrip..."
python -c "
from src.main import TranslationEngine
from pathlib import Path

engine = TranslationEngine()
result = engine.translate(
    input_file=Path('$INPUT_FILE'),
    output_file=Path('output/spectre_to_spectre/gpdk090_capacitor.scs'),
    source_format='spectre',
    target_format='spectre',
    validate=False
)
print(f'✅ Spectre: {result[\"models_translated\"]} models' if result['success'] else f'❌ Spectre failed')
"

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "4️⃣ Output Comparison"
echo ""

echo "📄 ngspice (lowered to primitives):"
echo "-----------------------------------"
head -35 output/spectre_to_ngspice/gpdk090_capacitor.lib | tail -20

echo ""
echo "📄 HSPICE (lowered to primitives):"
echo "-----------------------------------"
head -35 output/spectre_to_hspice/gpdk090_capacitor.sp | tail -20

echo ""
echo "📄 Spectre (native format preserved):"
echo "--------------------------------------"
head -35 output/spectre_to_spectre/gpdk090_capacitor.scs | tail -20

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "5️⃣ Verification"
echo ""

# Check ngspice has primitives
if grep -q "^Carea.*{.*area.*}" output/spectre_to_ngspice/gpdk090_capacitor.lib && \
   grep -q "^Csw.*{.*perim.*}" output/spectre_to_ngspice/gpdk090_capacitor.lib; then
    echo "✅ ngspice: Capacitors lowered to primitives (C{expr})"
else
    echo "❌ ngspice: Lowering failed"
    exit 1
fi

# Check HSPICE has primitives (uses C='expr' syntax)
if grep -q "^Carea.*=.*area" output/spectre_to_hspice/gpdk090_capacitor.sp && \
   grep -q "^Csw.*=.*perim" output/spectre_to_hspice/gpdk090_capacitor.sp; then
    echo "✅ HSPICE: Capacitors lowered to primitives (C='expr')"
else
    echo "❌ HSPICE: Lowering failed"
    exit 1
fi

# Check Spectre preserved native format
if grep -q "inline subckt" output/spectre_to_spectre/gpdk090_capacitor.scs && \
   grep -q "model.*capacitor" output/spectre_to_spectre/gpdk090_capacitor.scs; then
    echo "✅ Spectre: Native format preserved"
else
    echo "❌ Spectre: Format not preserved"
    exit 1
fi

echo ""
echo "🎉 ALL BACKENDS WORKING CORRECTLY"
