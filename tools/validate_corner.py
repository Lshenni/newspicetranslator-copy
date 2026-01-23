#!/usr/bin/env python3
"""
Corner validation - Validate translation across all MOS model corners
Run 10x with random PDK files and verify all corner models translate correctly
"""

import sys
from pathlib import Path
from collections import defaultdict
import random

# Add src to path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.main import TranslationEngine

def find_all_spectre_files():
    """Find all Spectre files in the PDK library"""
    libs_dir = BASE_DIR / 'tools/spice-libraries/private-models'
    if not libs_dir.exists():
        return []
    
    return list(libs_dir.rglob('*.scs'))

def extract_corners_from_file(filepath):
    """Extract all corner model names from a Spectre file"""
    corners = []
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line_stripped = line.strip()
            # Look for .model statements (older format)
            if line_stripped.startswith('.model '):
                parts = line_stripped.split()
                if len(parts) >= 3:
                    model_name = parts[1]
                    corners.append(model_name)
            # Look for model statements in Spectre format (more common)
            elif line_stripped.startswith('model ') and not line_stripped.startswith('//'):
                parts = line_stripped.split()
                if len(parts) >= 2:
                    model_name = parts[1]
                    corners.append(model_name)
            # Look for subcircuit definitions (also common in PDKs)
            elif line_stripped.startswith('subckt ') or line_stripped.startswith('.subckt '):
                parts = line_stripped.split()
                if len(parts) >= 2:
                    subckt_name = parts[1]
                    corners.append(subckt_name)
    return corners

def validate_corner_translation(input_file, target, corner_name):
    """
    Validate that a specific corner model translates correctly
    Returns dict with success status and details
    """
    engine = TranslationEngine()
    output_dir = BASE_DIR / 'output/validation_corners' / target
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{input_file.stem}_{corner_name}.lib"
    
    try:
        result = engine.translate(
            input_file=input_file,
            output_file=output_file,
            source_format='spectre',
            target_format=target
        )
        
        models_count = result.get('models_translated', 0)
        
        # Check if the output contains this specific corner
        if output_file.exists():
            content = output_file.read_text(encoding='utf-8', errors='ignore')
            corner_found = corner_name.lower() in content.lower()
        else:
            corner_found = False
        
        return {
            'success': result.get('success', False) and corner_found,
            'models': models_count,
            'corner_found': corner_found,
            'size': output_file.stat().st_size if output_file.exists() else 0,
            'error': result.get('error', None)
        }
    except Exception as e:
        return {
            'success': False,
            'models': 0,
            'corner_found': False,
            'size': 0,
            'error': str(e)
        }

def main():
    """Run corner validation across random PDK files"""
    all_files = find_all_spectre_files()
    
    if not all_files:
        print("❌ No Spectre files found!")
        return
    
    # Filter for MOS files (most likely to have corners)
    mos_files = [f for f in all_files if 'mos' in f.stem.lower()]
    if not mos_files:
        mos_files = all_files  # Fallback to all files
    
    print(f"📁 Found {len(mos_files)} MOS-related files")
    
    # Results tracking
    stats = defaultdict(lambda: {
        'total_corners': 0,
        'corners_translated': 0,
        'corners_failed': 0,
        'errors': []
    })
    
    backends = ['ngspice', 'hspice', 'spectre']
    iterations = 10
    
    print(f"\n🔬 Running {iterations} iterations × {len(backends)} backends")
    print("🎯 Validating corner-level translation")
    print("=" * 70)
    
    for iteration in range(1, iterations + 1):
        # Select random MOS files
        selected = random.choices(mos_files, k=min(3, len(mos_files)))
        
        print(f"\n▶ Iteration {iteration}/{iterations}")
        
        for input_file in selected:
            # Extract all corners from this file
            corners = extract_corners_from_file(input_file)
            
            if not corners:
                print(f"   ⊘  {input_file.stem}: No corners found (skipped)")
                continue
            
            print(f"   📄 {input_file.stem}: Found {len(corners)} corners")
            
            # Test each backend with first 3 corners (representative sample)
            sample_corners = corners[:min(3, len(corners))]
            
            for target in backends:
                for corner in sample_corners:
                    key = f"{input_file.stem}/{corner} → {target}"
                    result = validate_corner_translation(input_file, target, corner)
                    
                    stats[target]['total_corners'] += 1
                    
                    if result['success']:
                        stats[target]['corners_translated'] += 1
                        print(f"      ✅ {corner} → {target}")
                    else:
                        stats[target]['corners_failed'] += 1
                        stats[target]['errors'].append(f"{corner}: {result['error']}")
                        print(f"      ❌ {corner} → {target}: {result['error']}")
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 CORNER VALIDATION SUMMARY")
    print("=" * 70)
    
    for backend in backends:
        data = stats[backend]
        total = data['total_corners']
        success = data['corners_translated']
        failed = data['corners_failed']
        
        if total > 0:
            success_rate = 100 * success / total
            print(f"\n{backend.upper()}:")
            print(f"  Total corners tested: {total}")
            print(f"  ✅ Translated: {success} ({success_rate:.1f}%)")
            print(f"  ❌ Failed: {failed} ({100*failed/total:.1f}%)")
            
            if failed > 0 and data['errors']:
                print(f"  Top errors:")
                # Show first 3 unique errors
                unique_errors = list(set(data['errors']))[:3]
                for err in unique_errors:
                    print(f"    - {err[:60]}")
    
    # Overall summary
    total_all = sum(s['total_corners'] for s in stats.values())
    success_all = sum(s['corners_translated'] for s in stats.values())
    
    if total_all > 0:
        print(f"\n🎯 OVERALL: {success_all}/{total_all} corners ({100*success_all/total_all:.1f}% success)")
    
    print("\n✅ Corner validation complete")

if __name__ == '__main__':
    main()
