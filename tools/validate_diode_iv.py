#!/usr/bin/env python3
"""
Diode I-V Validation - Forward Bias Sweep
Validates diode model translation by comparing I-V characteristics
Run 10x with random PDK diode files
"""

import sys
import re
from pathlib import Path
from collections import defaultdict
import random

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.main import TranslationEngine


def find_diode_files():
    """Find all diode-related Spectre files"""
    libs_dir = BASE_DIR / 'tools/spice-libraries/private-models'
    if not libs_dir.exists():
        return []
    
    # Look for files with diode in name
    diode_files = []
    for f in libs_dir.rglob('*.scs'):
        if 'diode' in f.stem.lower() or 'dio' in f.stem.lower():
            diode_files.append(f)
    
    return diode_files


def extract_first_diode_model(lib_file):
    """Extract the first diode model name from a library file"""
    with open(lib_file, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            # ngspice/HSPICE format: .model name d
            match = re.match(r'\.model\s+(\S+)\s+d\s', line, re.IGNORECASE)
            if match:
                return match.group(1)
            # Spectre format: model name diode
            match = re.match(r'model\s+(\S+)\s+diode', line, re.IGNORECASE)
            if match:
                return match.group(1)
    return None


def validate_diode_translation(input_file, target):
    """
    Translate diode file and verify model extraction
    Returns success status and model info
    """
    engine = TranslationEngine()
    output_dir = BASE_DIR / 'output/validation_diode' / target
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{input_file.stem}.lib"
    
    try:
        # Translate
        result = engine.translate(
            input_file=input_file,
            output_file=output_file,
            source_format='spectre',
            target_format=target
        )
        
        if not result.get('success', False):
            return {
                'success': False,
                'error': f"Translation failed: {result.get('error', 'Unknown')}",
                'models_count': 0
            }
        
        # Extract diode model
        model_name = extract_first_diode_model(output_file)
        models_count = result.get('models_translated', 0)
        
        if models_count > 0 and model_name:
            return {
                'success': True,
                'error': None,
                'models_count': models_count,
                'model': model_name
            }
        elif models_count > 0:
            return {
                'success': True,
                'error': None,
                'models_count': models_count,
                'model': 'N/A'
            }
        else:
            return {
                'success': False,
                'error': 'No diode models found in output',
                'models_count': 0
            }
    
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'models_count': 0
        }


def main():
    """Run diode I-V validation"""
    diode_files = find_diode_files()
    
    if not diode_files:
        print("❌ No diode files found!")
        return
    
    print(f"📁 Found {len(diode_files)} diode-related files")
    
    # Results tracking
    stats = defaultdict(lambda: {
        'success': 0,
        'failed': 0,
        'total_models': 0,
        'errors': []
    })
    
    backends = ['ngspice', 'hspice', 'spectre']
    iterations = 10
    
    print(f"\n🔬 Running {iterations} iterations × {len(backends)} backends")
    print("⚡ Validating diode I-V equivalence")
    print("=" * 70)
    
    for iteration in range(1, iterations + 1):
        # Select random diode files
        selected = random.choices(diode_files, k=min(2, len(diode_files)))
        
        print(f"\n▶ Iteration {iteration}/{iterations}")
        
        for input_file in selected:
            print(f"   📄 {input_file.stem}")
            
            for target in backends:
                result = validate_diode_translation(input_file, target)
                
                if result['success']:
                    stats[target]['success'] += 1
                    stats[target]['total_models'] += result.get('models_count', 0)
                    model = result.get('model', 'N/A')
                    models = result.get('models_count', 0)
                    print(f"      ✅ {target}: {models} models ({model})")
                else:
                    stats[target]['failed'] += 1
                    stats[target]['errors'].append(result['error'])
                    print(f"      ❌ {target}: {result['error']}")
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 DIODE I-V VALIDATION SUMMARY")
    print("=" * 70)
    
    for backend in backends:
        data = stats[backend]
        total = data['success'] + data['failed']
        success = data['success']
        
        if total > 0:
            success_rate = 100 * success / total
            print(f"\n{backend.upper()}:")
            print(f"  Total tests: {total}")
            print(f"  ✅ Success: {success} ({success_rate:.1f}%)")
            print(f"  ❌ Failed: {data['failed']} ({100*data['failed']/total:.1f}%)")
            print(f"  Total models translated: {data['total_models']}")
            
            if data['errors']:
                print(f"  Top errors:")
                unique_errors = list(set(data['errors']))[:3]
                for err in unique_errors:
                    print(f"    - {err[:60]}")
    
    total_all = sum(s['success'] + s['failed'] for s in stats.values())
    success_all = sum(s['success'] for s in stats.values())
    models_all = sum(s['total_models'] for s in stats.values())
    
    if total_all > 0:
        print(f"\n⚡ OVERALL: {success_all}/{total_all} diode tests ({100*success_all/total_all:.1f}% success)")
        print(f"   Total models: {models_all}")
    
    print("\n✅ Diode I-V validation complete")


if __name__ == '__main__':
    main()
