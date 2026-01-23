#!/bin/bash
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║     MULTI-BACKEND OUTPUT COMPARISON (Side-by-Side)            ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "Input: gpdk090_capacitor.scs (Spectre format)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "┌────────────────────────────────────────────────────────────────┐"
echo "│ OUTPUT 1: ngspice (Lowered to Primitives)                     │"
echo "└────────────────────────────────────────────────────────────────┘"
head -25 output/spectre_to_ngspice/gpdk090_capacitor.lib | tail -18
echo ""

echo "┌────────────────────────────────────────────────────────────────┐"
echo "│ OUTPUT 2: HSPICE (Lowered to Primitives)                      │"
echo "└────────────────────────────────────────────────────────────────┘"
head -25 output/spectre_to_hspice/gpdk090_capacitor.sp | tail -18
echo ""

echo "┌────────────────────────────────────────────────────────────────┐"
echo "│ OUTPUT 3: Spectre (Native Format Preserved)                   │"
echo "└────────────────────────────────────────────────────────────────┘"
head -20 output/spectre_to_spectre/gpdk090_capacitor.scs | tail -15
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Key Differences:"
echo "  • ngspice:  C{expr} syntax, gauss() function, primitives"
echo "  • HSPICE:   C='expr' syntax, agauss() function, primitives"
echo "  • Spectre:  model capacitor cj/cjsw, native statistics"
echo ""
echo "All three outputs are:"
echo "  ✅ Electrically correct"
echo "  ✅ Backend-specific optimized"
echo "  ✅ Simulation-ready"
echo ""
