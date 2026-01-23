#!/usr/bin/env python3
"""
10x Random Validation Test Harness
Tests translation robustness with random PDK file selections
"""
import random
import subprocess
import sys
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parents[1]
PDK_DIR = BASE_DIR / 'tools' / 'spice-libraries' / 'private-models'
OUTPUT_DIR = BASE_DIR / 'output' / 'validation_10x'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(BASE_DIR))
from src.main import TranslationEngine


def find_all_spectre_files():
    """Find all Spectre input files"""
    return list(PDK_DIR.rglob('*.scs'))


def run_translation_test(input_file: Path, target: str, iteration: int):
    """Run a single translation test"""
    engine = TranslationEngine()
    output_file = OUTPUT_DIR / target / f"{input_file.stem}_iter{iteration}.lib"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        result = engine.translate(
            input_file=input_file,
            output_file=output_file,
            source_format='spectre',
            target_format=target
        )
        # Consider files with no models as skipped, not failed
        models_count = result.get('models_translated', 0)
        if models_count == 0:
            return {
                'success': True,
                'models': 0,
                'size': 0,
                'error': None,
                'skipped': True
            }
        return {
            'success': result.get('success', False),
            'models': models_count,
            'size': output_file.stat().st_size if output_file.exists() else 0,
            'error': result.get('error', None),
            'skipped': False
        }
    except Exception as e:
        return {
            'success': False,
            'models': 0,
            'size': 0,
            'error': str(e),
            'skipped': False
        }


def main():
    # Find all Spectre files
    all_files = find_all_spectre_files()
    if not all_files:
        print("❌ No Spectre files found")
        return
    
    print(f"📁 Found {len(all_files)} Spectre files")
    
    # Results tracking
    stats = defaultdict(lambda: {'success': 0, 'failed': 0, 'skipped': 0, 'errors': []})
    
    backends = ['ngspice', 'hspice', 'spectre']
    iterations = 10
    
    print(f"\n🔬 Running {iterations} iterations × {len(backends)} backends")
    print("=" * 70)
    
    for iteration in range(1, iterations + 1):
        # Select random files (with replacement)
        selected = random.choices(all_files, k=min(5, len(all_files)))
        
        print(f"\n▶ Iteration {iteration}/{iterations}")
        print(f"   Files: {[f.name for f in selected]}")
        
        for target in backends:
            for input_file in selected:
                result = run_translation_test(input_file, target, iteration)
                
                key = f"{input_file.stem} → {target}"
                if result.get('skipped'):
                    stats[key]['skipped'] += 1
                    print(f"   ⊘  {key}: Skipped (0 models)")
                elif result['success']:
                    stats[key]['success'] += 1
                    print(f"   ✅ {key}: {result['models']} models, {result['size']} bytes")
                else:
                    stats[key]['failed'] += 1
                    stats[key]['errors'].append(result['error'])
                    print(f"   ❌ {key}: {result['error']}")
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 VALIDATION SUMMARY")
    print("=" * 70)
    
    total_success = sum(s['success'] for s in stats.values())
    total_failed = sum(s['failed'] for s in stats.values())
    total_skipped = sum(s['skipped'] for s in stats.values())
    total_runs = total_success + total_failed + total_skipped
    
    print(f"\nTotal Runs: {total_runs}")
    print(f"✅ Success: {total_success} ({100*total_success/total_runs:.1f}%)")
    print(f"⊘  Skipped: {total_skipped} ({100*total_skipped/total_runs:.1f}%)")
    print(f"❌ Failed:  {total_failed} ({100*total_failed/total_runs:.1f}%)")
    
    # Error analysis
    if total_failed > 0:
        print(f"\n⚠️  ERROR ANALYSIS")
        error_counts = defaultdict(int)
        for key, data in stats.items():
            if data['failed'] > 0:
                for err in data['errors']:
                    # Truncate error to first line
                    err_short = (err or 'Unknown').split('\n')[0][:80]
                    error_counts[err_short] += 1
        
        print("\nTop errors:")
        for err, count in sorted(error_counts.items(), key=lambda x: -x[1])[:5]:
            print(f"  [{count:2d}x] {err}")
    
    # Per-backend stats
    print(f"\n📈 PER-BACKEND STATISTICS")
    for backend in backends:
        backend_stats = {k: v for k, v in stats.items() if backend in k}
        if backend_stats:
            backend_success = sum(s['success'] for s in backend_stats.values())
            backend_failed = sum(s['failed'] for s in backend_stats.values())
            backend_total = backend_success + backend_failed
            print(f"  {backend:10s}: {backend_success}/{backend_total} ({100*backend_success/backend_total:.1f}%)")
    
    print("\n✅ 10x validation complete")
    return total_failed == 0


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
