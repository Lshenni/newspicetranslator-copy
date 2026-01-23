#!/usr/bin/env python3
"""Test enhanced extraction for gpdk090_capacitor.scs"""

from pathlib import Path
from src.parsers.spectre_parser import SpectreParser

parser = SpectreParser(Path('tools/spice-libraries/private-models/cadence90/spectre/gpdk090_capacitor.scs'))
content = parser.content

print("=" * 70)
print("ENHANCED EXTRACTION TEST")
print("=" * 70)

# Test subcircuit extraction
subcircuits = parser.extract_subcircuits(content)
print(f"\n📦 Subcircuits extracted: {len(subcircuits)}")
for s in subcircuits:
    print(f"\n  Subcircuit: {s.name}")
    print(f"    Ports: {', '.join(s.ports)}")
    print(f"    Parameters: {s.parameters}")
    print(f"    Elements: {len(s.elements)} lines")
    for elem in s.elements[:3]:
        print(f"      - {elem}")
    if len(s.elements) > 3:
        print(f"      ... and {len(s.elements) - 3} more")

# Test section extraction
sections = parser.extract_sections(content)
print(f"\n🔧 Sections extracted: {len(sections)}")
for name, params in sorted(sections.items()):
    print(f"  - {name:15s} : {params}")

# Test statistics extraction
stats = parser.extract_statistics(content)
print(f"\n📊 Statistics: {stats is not None}")
if stats:
    print(f"  Variables: {len(stats.variables)}")
    for var, info in stats.variables.items():
        print(f"    - {var:10s} : dist={info['distribution']:8s} std={info['std']}")

# Test full IR
print("\n" + "=" * 70)
print("FULL IR EXTRACTION")
print("=" * 70)

ir_models = parser.parse_to_ir()
print(f"\nIR Models: {len(ir_models)}")
for model in ir_models:
    print(f"\n  Model: {model.name}")
    print(f"    Device Type: {model.device_type.value}")
    print(f"    Parameters: {len(model.base_parameters)}")
    for pname, pval in list(model.base_parameters.items())[:3]:
        print(f"      - {pname} = {pval}")
    print(f"    Subcircuits: {len(model.subcircuits)}")
    for s in model.subcircuits:
        print(f"      - {s.name} ({len(s.ports)} ports)")
    print(f"    Statistical: {model.statistical is not None}")
    if model.statistical:
        print(f"      Variables: {list(model.statistical.variables.keys())}")
    print(f"    Metadata: {model.metadata}")

print("\n" + "=" * 70)
print("✅ EXTRACTION COMPLETE")
print("=" * 70)
