#!/usr/bin/env python3
"""
SPICE Translator CLI with Verification

Command-line interface for translation and verification workflows.

Examples:
    # Translate only
    ./cli.py translate gpdk090_mos.scs --target ngspice
    
    # Verify translation
    ./cli.py verify gpdk090_capacitor.scs mimcap --source spectre --target ngspice
    
    # Verify with Monte Carlo
    ./cli.py verify gpdk090_capacitor.scs mimcap --runs 500 --strict
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from src.main import TranslationEngine
from verification.verifier import Verifier, VerificationError


def cmd_translate(args):
    """Handle translate command"""
    engine = TranslationEngine()
    
    input_file = Path(args.input)
    output_file = Path(args.output) if args.output else input_file.with_suffix('.lib')
    
    result = engine.translate(
        input_file=input_file,
        output_file=output_file,
        source_format=args.source,
        target_format=args.target
    )
    
    if result.get('success'):
        print(f"✅ Translation successful: {output_file}")
        print(f"   Models translated: {result.get('models_translated', 0)}")
        print(f"   Output size: {output_file.stat().st_size} bytes")
    else:
        print(f"❌ Translation failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)


def cmd_verify(args):
    """Handle verify command"""
    verifier = Verifier(
        monte_carlo_runs=args.runs,
        strict=args.strict
    )
    
    # Parse device parameters
    device_params = {}
    if args.area:
        device_params['area'] = float(args.area)
    if args.perim:
        device_params['perim'] = float(args.perim)
    if args.width:
        device_params['width'] = float(args.width)
    if args.length:
        device_params['length'] = float(args.length)
    
    try:
        report = verifier.verify(
            device_file=Path(args.input),
            device_name=args.device,
            device_class=args.device_class,
            source_format=args.source,
            target_format=args.target,
            **device_params
        )
        
        print(report)

        if getattr(report, 'skipped', False):
            print("\n⚠️  VERIFICATION SKIPPED (known limitation)")
            return

        if not report.passed:
            print("\n❌ VERIFICATION FAILED")
            sys.exit(1)
        else:
            print("\n✅ VERIFICATION PASSED")
    
    except VerificationError as e:
        print(f"\n❌ VERIFICATION ERROR: {e}")
        sys.exit(1)


def cmd_verify_all(args):
    """Handle verify all command (for regression/CI)"""
    print("🔬 Running regression verification suite...")
    print("="*70)
    
    # Define test suite
    test_cases = [
        {
            'input': 'tools/spice-libraries/private-models/cadence90/spectre/gpdk090_capacitor.scs',
            'device': 'gpdk090_mimcap',
            'device_class': 'capacitor',
            'area': 10e-6,
            'perim': 20e-6
        },
        {
            'input': 'tools/spice-libraries/private-models/cadence90/spectre/gpdk090_diode.scs',
            'device': 'gpdk090_ndio',
            'device_class': 'diode'
        }
    ]
    
    passed = 0
    failed = 0
    skipped = 0
    
    verifier = Verifier(strict=args.strict)
    
    for test in test_cases:
        device_name = test['device']
        print(f"\n▶ Testing {device_name}...")
        
        try:
            report = verifier.verify(
                device_file=Path(BASE_DIR / test['input']),
                device_name=device_name,
                device_class=test['device_class'],
                source_format=args.source,
                target_format=args.target,
                **{k: v for k, v in test.items() if k not in ['input', 'device', 'device_class']}
            )
            
            if report.passed:
                print(f"  ✅ PASS")
                passed += 1
            elif getattr(report, 'skipped', False):
                print(f"  ⚠️  SKIP ({getattr(report, 'skip_reason', 'known limitation')})")
                skipped += 1
            else:
                print(f"  ❌ FAIL")
                print(f"     {report.errors}")
                failed += 1
        
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            failed += 1
    
    print("\n" + "="*70)
    print(f"📊 Regression Results: {passed} passed, {skipped} skipped, {failed} failed")
    
    if failed > 0:
        print("❌ REGRESSION FAILED")
        sys.exit(1)
    else:
        print("✅ REGRESSION PASSED")


def main():
    parser = argparse.ArgumentParser(
        description='SPICE Translator with Verification',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Translate:
    %(prog)s translate input.scs --target ngspice
    
  Verify:
    %(prog)s verify gpdk090_capacitor.scs mimcap --device-class capacitor --area 10e-6
    
  Verify with Monte Carlo:
    %(prog)s verify gpdk090_mos.scs nmos1v --device-class mos --runs 500 --strict
    
  Regression (CI):
    %(prog)s verify-all --target ngspice
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Translate command
    translate_parser = subparsers.add_parser('translate', help='Translate SPICE file')
    translate_parser.add_argument('input', help='Input SPICE file')
    translate_parser.add_argument('--output', '-o', help='Output file (default: input with .lib extension)')
    translate_parser.add_argument('--source', '-s', default='spectre', 
                                  choices=['spectre', 'hspice', 'ngspice'],
                                  help='Source format')
    translate_parser.add_argument('--target', '-t', required=True,
                                  choices=['spectre', 'hspice', 'ngspice'],
                                  help='Target format')
    
    # Verify command
    verify_parser = subparsers.add_parser('verify', help='Verify translation with simulation')
    verify_parser.add_argument('input', help='Input device library file')
    verify_parser.add_argument('device', help='Device/model name to verify')
    verify_parser.add_argument('--device-class', '-c', required=True,
                               choices=['capacitor', 'resistor', 'mos', 'bjt', 'diode'],
                               help='Device class')
    verify_parser.add_argument('--source', '-s', default='spectre',
                              choices=['spectre', 'hspice', 'ngspice'],
                              help='Source format')
    verify_parser.add_argument('--target', '-t', required=True,
                              choices=['spectre', 'hspice', 'ngspice'],
                              help='Target format')
    verify_parser.add_argument('--runs', '-r', type=int, default=0,
                              help='Monte Carlo runs (0 = disabled)')
    verify_parser.add_argument('--strict', action='store_true',
                              help='Use strict tolerances')
    verify_parser.add_argument('--area', type=float, help='Device area (capacitor)')
    verify_parser.add_argument('--perim', type=float, help='Device perimeter (capacitor)')
    verify_parser.add_argument('--width', '-w', type=float, help='Device width (MOS)')
    verify_parser.add_argument('--length', '-l', type=float, help='Device length (MOS)')
    
    # Verify all command (regression)
    verify_all_parser = subparsers.add_parser('verify-all', help='Run regression verification')
    verify_all_parser.add_argument('--source', '-s', default='spectre',
                                   choices=['spectre', 'hspice', 'ngspice'],
                                   help='Source format')
    verify_all_parser.add_argument('--target', '-t', default='ngspice',
                                   choices=['spectre', 'hspice', 'ngspice'],
                                   help='Target format')
    verify_all_parser.add_argument('--strict', action='store_true',
                                   help='Use strict tolerances')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if args.command == 'translate':
        cmd_translate(args)
    elif args.command == 'verify':
        cmd_verify(args)
    elif args.command == 'verify-all':
        cmd_verify_all(args)


if __name__ == '__main__':
    main()
