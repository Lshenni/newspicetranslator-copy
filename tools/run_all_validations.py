#!/usr/bin/env python3
"""
Master Validation Runner
Runs all validation phases in sequence and generates final report
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
TOOLS_DIR = BASE_DIR / 'tools'


def run_validation(script_name, description, timeout=180):
    """Run a validation script and capture results"""
    print(f"\n{'='*70}")
    print(f"🔬 {description}")
    print(f"{'='*70}\n")
    
    script_path = TOOLS_DIR / script_name
    
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=BASE_DIR
        )
        
        # Print stdout (filtered for summary)
        for line in result.stdout.split('\n'):
            # Skip verbose INFO/WARNING logs
            if line.startswith('INFO:') or line.startswith('WARNING:'):
                continue
            if line.strip():
                print(line)
        
        if result.returncode == 0:
            print(f"\n✅ {description} completed successfully")
            return True
        else:
            print(f"\n❌ {description} failed with return code {result.returncode}")
            if result.stderr:
                print(f"Error output:\n{result.stderr}")
            return False
    
    except subprocess.TimeoutExpired:
        print(f"\n⏱️  {description} timed out after {timeout}s")
        return False
    except Exception as e:
        print(f"\n❌ {description} failed: {e}")
        return False


def main():
    """Run all validation phases"""
    start_time = datetime.now()
    
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║         SPICE TRANSLATOR - COMPREHENSIVE VALIDATION SUITE          ║")
    print("║                     10x Random Testing Framework                   ║")
    print("╚════════════════════════════════════════════════════════════════════╝")
    print(f"\nStart time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    validations = [
        {
            'script': 'validate_10x.py',
            'desc': 'Phase 1.2: File-Level Random Validation (10x)',
            'timeout': 180
        },
        {
            'script': 'validate_corner.py',
            'desc': 'Phase 1.3: Corner-Level Validation',
            'timeout': 180
        },
        {
            'script': 'validate_bjt_numeric.py',
            'desc': 'Phase 2.1: BJT Numeric Validation',
            'timeout': 120
        },
        {
            'script': 'validate_diode_iv.py',
            'desc': 'Phase 2.2: Diode I-V Validation',
            'timeout': 120
        }
    ]
    
    results = {}
    
    for val in validations:
        success = run_validation(val['script'], val['desc'], val['timeout'])
        results[val['desc']] = success
    
    # Summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print("\n" + "="*70)
    print("📊 FINAL VALIDATION SUMMARY")
    print("="*70)
    
    total_phases = len(results)
    successful_phases = sum(1 for success in results.values() if success)
    
    print(f"\nTotal validation phases: {total_phases}")
    print(f"✅ Successful: {successful_phases}")
    print(f"❌ Failed: {total_phases - successful_phases}")
    
    print("\nPhase-by-phase results:")
    for phase, success in results.items():
        status = "✅" if success else "❌"
        print(f"  {status} {phase}")
    
    print(f"\nTotal runtime: {duration:.1f}s ({duration/60:.1f} minutes)")
    print(f"End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Overall status
    if successful_phases == total_phases:
        print("\n🎉 ALL VALIDATION PHASES PASSED!")
        print("   Project status: PRODUCTION-READY ✅")
        return 0
    else:
        print(f"\n⚠️  {total_phases - successful_phases} validation phase(s) failed")
        print("   Review errors above for details")
        return 1


if __name__ == '__main__':
    sys.exit(main())
