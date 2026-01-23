#!/bin/bash
echo "======================================================================"
echo "FINAL DEMONSTRATION: Enhanced SPICE Translation"
echo "======================================================================"
echo ""

echo "📊 Test File: gpdk090_capacitor.scs"
echo "----------------------------------------------------------------------"
wc -l tools/spice-libraries/private-models/cadence90/spectre/gpdk090_capacitor.scs
echo ""

echo "🔍 Step 1: Enhanced Extraction Test"
echo "----------------------------------------------------------------------"
python3 test_extraction.py 2>&1 | grep -A 20 "ENHANCED EXTRACTION"
echo ""

echo "🔄 Step 2: Translation (Spectre → ngspice)"
echo "----------------------------------------------------------------------"
python3 -m src.main translate \
    tools/spice-libraries/private-models/cadence90/spectre/gpdk090_capacitor.scs \
    --from spectre --to ngspice 2>&1 | grep -E "(INFO|✓)"
echo ""

echo "📄 Step 3: Output File Statistics"
echo "----------------------------------------------------------------------"
echo "Lines: $(wc -l < output/spectre_to_ngspice/gpdk090_capacitor.lib)"
echo "Bytes: $(wc -c < output/spectre_to_ngspice/gpdk090_capacitor.lib)"
echo ""

echo "📋 Step 4: Output File Content"
echo "----------------------------------------------------------------------"
cat output/spectre_to_ngspice/gpdk090_capacitor.lib
echo ""

echo "✅ Step 5: Verification Summary"
echo "----------------------------------------------------------------------"
echo "✓ Parameters extracted: $(grep -c 'cj=' output/spectre_to_ngspice/gpdk090_capacitor.lib) model parameters"
echo "✓ Subcircuits: $(grep -c '.subckt' output/spectre_to_ngspice/gpdk090_capacitor.lib) subcircuit definitions"
echo "✓ Statistical vars: $(grep -c '.param pc_mc' output/spectre_to_ngspice/gpdk090_capacitor.lib) statistical parameters"
echo ""

echo "======================================================================"
echo "✅ DEMONSTRATION COMPLETE"
echo "======================================================================"
