#!/usr/bin/env python3
"""
Batch Verification Runner for All Translated PDKs

Runs enhanced verification on all PDK outputs and generates a comprehensive report.

Usage:
    python batch_verify.py [--output report.json] [--quick]
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from verification.enhanced_verifier import EnhancedVerifier


def run_batch_verification(
    output_dir: Path,
    quick_mode: bool = False,
    monte_carlo_runs: int = 0,
    include_roundtrip: bool = False
) -> Dict[str, Any]:
    """Run verification on all PDK output directories"""
    
    verifier = EnhancedVerifier(verbose=False)

    def _classify_test(test) -> str:
        """Classify a test result into a reviewer-facing outcome bucket."""
        details = getattr(test, 'details', {}) or {}
        message = (getattr(test, 'message', '') or '').lower()

        if details.get('skipped'):
            if details.get('simulator_constraint') == 'bsim4_parameter_check' or (
                'bsim4' in message and 'constraint' in message
            ):
                return 'simulator_guardrail'
            if details.get('reason') == 'singular_matrix' or 'singular matrix' in message or 'numerical constraint' in message:
                return 'non_critical'
            return 'other_skipped'

        if not getattr(test, 'passed', False):
            return 'translator_defect'

        return 'clean_pass'

    def _is_verifiable_output(path: Path) -> bool:
        return path.is_file() and path.suffix.lower() == '.lib'

    def _normalize_pdk_name(folder_name: str) -> str:
        """Normalize output folder names across both translation directions."""
        for suffix in (
            '_hspice-ngspice', '_spectre-ngspice',
            '_ngspice-hspice', '_ngspice-spectre',
            '-ngspice', '_hspice', '_spectre'
        ):
            folder_name = folder_name.replace(suffix, '')
        return folder_name
    
    # Find all PDK output directories
    pdk_dirs = sorted([d for d in output_dir.iterdir() 
                       if d.is_dir() and (
                           d.name.endswith('_hspice-ngspice') or
                           d.name.endswith('_spectre-ngspice')
                       )])
    
    print(f"Found {len(pdk_dirs)} PDK output directories to verify")
    print("=" * 70)
    
    all_results = {
        'timestamp': datetime.now().isoformat(),
        'mode': 'quick' if quick_mode else 'full',
        'pdks': {},
        'summary': {
            'total_pdks': len(pdk_dirs),
            'total_files': 0,
            'total_tests': 0,
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'roundtrip_passed': 0,
            'roundtrip_failed': 0,
            'monte_carlo_passed': 0,
            'monte_carlo_failed': 0,
            'label_counts': {
                'translator_defect': 0,
                'simulator_guardrail': 0,
                'non_critical': 0,
                'other_skipped': 0,
                'clean_pass': 0
            }
        }
    }
    
    for pdk_dir in pdk_dirs:
        pdk_name = _normalize_pdk_name(pdk_dir.name)
        print(f"\n📁 {pdk_name}")
        
        # Find .lib files case-insensitively and recursively
        lib_files = sorted([f for f in pdk_dir.rglob('*') if _is_verifiable_output(f)])
        if not lib_files:
            print(f"   No .lib files found, skipping")
            continue
        
        pdk_results = {
            'files': [],
            'summary': {
                'total_files': len(lib_files),
                'total_tests': 0,
                'passed': 0,
                'failed': 0,
                'bsim4_errors': 0,
                'label_counts': {
                    'translator_defect': 0,
                    'simulator_guardrail': 0,
                    'non_critical': 0,
                    'other_skipped': 0,
                    'clean_pass': 0
                }
            }
        }
        
        # In quick mode, only test first 2 files per PDK
        files_to_test = lib_files[:2] if quick_mode else lib_files[:5]
        
        for lib_file in files_to_test:
            print(f"   📄 {lib_file.name}... ", end='', flush=True)
            
            try:
                results = verifier.run_full_verification(
                    lib_file,
                    include_roundtrip=include_roundtrip,
                    source_format_for_roundtrip='ngspice',
                    monte_carlo_runs=monte_carlo_runs
                )
                
                file_result = {
                    'name': lib_file.name,
                    'tests': results['summary']['total'],
                    'passed': results['summary']['passed'],
                    'failed': results['summary']['failed'],
                    'pass_rate': results['summary']['passed'] / max(results['summary']['total'], 1),
                    'failures': [],
                    'test_results': []
                }
                
                # Collect failure details
                for test in results['tests']:
                    label = _classify_test(test)
                    all_results['summary']['label_counts'][label] = all_results['summary']['label_counts'].get(label, 0) + 1
                    pdk_results['summary']['label_counts'][label] = pdk_results['summary']['label_counts'].get(label, 0) + 1

                    if test.test_name == 'roundtrip':
                        if test.passed:
                            all_results['summary']['roundtrip_passed'] += 1
                        else:
                            all_results['summary']['roundtrip_failed'] += 1
                    elif test.test_name == 'monte_carlo':
                        if test.passed:
                            all_results['summary']['monte_carlo_passed'] += 1
                        else:
                            all_results['summary']['monte_carlo_failed'] += 1

                    if not test.passed and not test.details.get('skipped'):
                        failure_info = {
                            'test': test.test_name,
                            'message': test.message[:100]
                        }
                        file_result['failures'].append(failure_info)
                        
                        # Check for BSIM4 errors specifically
                        if 'BSIM4' in test.message or 'bsim4' in str(test.details).lower():
                            pdk_results['summary']['bsim4_errors'] += 1

                    file_result['test_results'].append({
                        'test_name': test.test_name,
                        'passed': test.passed,
                        'label': label,
                        'message': test.message,
                        'details': test.details,
                        'warnings': test.warnings,
                    })
                
                pdk_results['files'].append(file_result)
                pdk_results['summary']['total_tests'] += file_result['tests']
                pdk_results['summary']['passed'] += file_result['passed']
                pdk_results['summary']['failed'] += file_result['failed']
                
                # Update global summary
                all_results['summary']['total_files'] += 1
                all_results['summary']['total_tests'] += file_result['tests']
                all_results['summary']['passed'] += file_result['passed']
                all_results['summary']['failed'] += file_result['failed']
                
                status = "✅" if file_result['failed'] == 0 else "❌"
                print(f"{status} {file_result['passed']}/{file_result['tests']}")
                
            except Exception as e:
                print(f"❌ Error: {str(e)[:50]}")
                pdk_results['files'].append({
                    'name': lib_file.name,
                    'error': str(e)[:200]
                })
        
        all_results['pdks'][pdk_name] = pdk_results
    
    return all_results


def print_summary(results: Dict[str, Any]):
    """Print a summary report"""
    print("\n")
    print("=" * 70)
    print("BATCH VERIFICATION SUMMARY")
    print("=" * 70)
    
    s = results['summary']
    pass_rate = s['passed'] / max(s['total_tests'], 1) * 100
    
    print(f"Timestamp:     {results['timestamp']}")
    print(f"Mode:          {results['mode']}")
    print(f"PDKs Tested:   {s['total_pdks']}")
    print(f"Files Tested:  {s['total_files']}")
    print(f"Total Tests:   {s['total_tests']}")
    print(f"Passed:        {s['passed']} ({pass_rate:.1f}%)")
    print(f"Failed:        {s['failed']}")
    if (s.get('roundtrip_passed', 0) + s.get('roundtrip_failed', 0)) > 0:
        rt_total = s['roundtrip_passed'] + s['roundtrip_failed']
        print(f"Round-trip:    {s['roundtrip_passed']}/{rt_total} passed")
    if (s.get('monte_carlo_passed', 0) + s.get('monte_carlo_failed', 0)) > 0:
        mc_total = s['monte_carlo_passed'] + s['monte_carlo_failed']
        print(f"Monte Carlo:   {s['monte_carlo_passed']}/{mc_total} passed")
    print()
    
    # Per-PDK summary
    print("PER-PDK RESULTS:")
    print("-" * 70)
    print(f"{'PDK':<30} {'Files':<8} {'Tests':<8} {'Pass%':<10} {'Status'}")
    print("-" * 70)
    
    for pdk_name, pdk_data in sorted(results['pdks'].items()):
        ps = pdk_data['summary']
        files = ps.get('total_files', len(pdk_data['files']))
        tests = ps['total_tests']
        passed = ps['passed']
        rate = passed / max(tests, 1) * 100
        
        status = "✅" if ps['failed'] == 0 else "❌"
        if ps.get('bsim4_errors', 0) > 0:
            status += f" (BSIM4: {ps['bsim4_errors']})"
        
        print(f"{pdk_name:<30} {files:<8} {tests:<8} {rate:>6.1f}%    {status}")
    
    print("-" * 70)
    
    # Failure analysis
    print("\nFAILURE ANALYSIS:")
    print("-" * 70)
    
    failure_types = {}
    for pdk_name, pdk_data in results['pdks'].items():
        for file_result in pdk_data['files']:
            for failure in file_result.get('failures', []):
                msg = failure['message']
                # Categorize failure
                if 'BSIM4' in msg or 'bsim4' in msg.lower():
                    category = 'BSIM4 parameter checking'
                elif 'convergence' in msg.lower():
                    category = 'Convergence issues'
                elif 'singular' in msg.lower():
                    category = 'Singular matrix'
                elif 'timeout' in msg.lower():
                    category = 'Timeout'
                else:
                    category = 'Other'
                
                failure_types[category] = failure_types.get(category, 0) + 1
    
    for category, count in sorted(failure_types.items(), key=lambda x: -x[1]):
        print(f"  {category}: {count}")
    
    print()


def main():
    parser = argparse.ArgumentParser(description="Batch PDK Verification")
    parser.add_argument('--output', '-o', type=Path, default=BASE_DIR / 'output' / 'verification_report.json',
                        help="Output JSON report path")
    parser.add_argument('--quick', '-q', action='store_true',
                        help="Quick mode: test fewer files per PDK")
    parser.add_argument('--mc-runs', type=int, default=0,
                        help="Monte Carlo runs per file (0 = disabled)")
    parser.add_argument('--roundtrip', action='store_true',
                        help="Include round-trip consistency check per file")
    parser.add_argument('--dir', '-d', type=Path, default=BASE_DIR / 'output',
                        help="Output directory containing PDK translations")
    
    args = parser.parse_args()
    
    print("🔬 SPICE Translator - Batch Verification")
    print("=" * 70)
    
    results = run_batch_verification(
        args.dir,
        quick_mode=args.quick,
        monte_carlo_runs=max(0, args.mc_runs),
        include_roundtrip=args.roundtrip
    )
    
    # Print summary
    print_summary(results)
    
    # Save JSON report
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"📊 Detailed report saved to: {args.output}")
    
    # Return success if pass rate > 80%
    pass_rate = results['summary']['passed'] / max(results['summary']['total_tests'], 1)
    return 0 if pass_rate >= 0.80 else 1


if __name__ == '__main__':
    sys.exit(main())
