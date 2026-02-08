#!/usr/bin/env python3
"""
SPICE Translator CLI with Verification and Plotting

Command-line interface for translation, verification, and plot generation.

Examples:
    # Translate only
    ./cli.py translate gpdk090_mos.scs --target ngspice
    
    # Translate with verification
    ./cli.py translate gpdk090_mos.scs --target ngspice --verify
    
    # Translate with verification and plots
    ./cli.py translate gpdk090_mos.scs --target ngspice --verify --plot
    
    # Verify translation
    ./cli.py verify gpdk090_capacitor.scs mimcap --source spectre --target ngspice
    
    # Generate verification plots for translated library
    ./cli.py plot output/translated.lib --max-devices 3
    
    # Generate plots for entire output directory
    ./cli.py plot output/cadence90_spectre-ngspice/
"""

import sys
import argparse
import subprocess
import tempfile
import re
from pathlib import Path

# Add project root to path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from src.main import TranslationEngine
from verification.verifier import Verifier, VerificationError


def cmd_translate(args):
    """Handle translate command"""
    engine = TranslationEngine()
    
    input_file = Path(args.input).resolve()
    
    if args.output:
        output_file = Path(args.output)
    else:
        # Auto-generate output path: output/{pdk_folder}_{source}-{target}/filename.ext
        # Try to find a meaningful parent folder (go up from format-specific folders like 'spectre', 'hspice')
        parent = input_file.parent
        format_folders = {'spectre', 'hspice', 'ngspice', 'lib', 'models'}
        
        # If parent is a format folder, use grandparent for PDK name
        if parent.name.lower() in format_folders:
            pdk_folder = parent.parent.name
        else:
            pdk_folder = parent.name
        
        folder_name = f"{pdk_folder}_{args.source}-{args.target}"
        output_dir = BASE_DIR / "output" / folder_name
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Determine output extension based on target format
        if args.target == 'spectre':
            ext = '.scs'
        else:
            ext = '.lib'
        
        output_file = output_dir / input_file.with_suffix(ext).name
    
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
        
        # Run verification if requested
        if args.verify and args.target == 'ngspice':
            print("\n🔬 Running ngspice verification...")
            verify_result = verify_ngspice_syntax(output_file)
            if verify_result['passed']:
                print(f"   ✅ Verification PASSED")
                if verify_result.get('device_name'):
                    print(f"   Device: {verify_result['device_name']} ({verify_result.get('device_type', 'unknown')})")
                
                # Generate plots if requested
                if args.plot:
                    print("\n📊 Generating verification plots...")
                    plot_result = generate_plots_for_file(output_file, max_devices=args.max_plots)
                    if plot_result['success']:
                        print(f"   ✅ Generated {plot_result['plot_count']} plots")
                        if plot_result.get('plot_dir'):
                            print(f"   Location: {plot_result['plot_dir']}")
                    else:
                        print(f"   ⚠️ Plot generation: {plot_result.get('error', 'No plots generated')}")
            else:
                print(f"   ❌ Verification FAILED: {verify_result.get('error', 'Unknown error')}")
                sys.exit(1)
        elif args.verify and args.target != 'ngspice':
            print(f"   ⚠️  Verification only supported for ngspice target (got {args.target})")
        elif args.plot and args.target == 'ngspice':
            # Plot without full verification
            print("\n📊 Generating verification plots...")
            plot_result = generate_plots_for_file(output_file, max_devices=args.max_plots)
            if plot_result['success']:
                print(f"   ✅ Generated {plot_result['plot_count']} plots")
                if plot_result.get('plot_dir'):
                    print(f"   Location: {plot_result['plot_dir']}")
            else:
                print(f"   ⚠️ Plot generation: {plot_result.get('error', 'No plots generated')}")
    else:
        print(f"❌ Translation failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)


def verify_ngspice_syntax(output_file: Path) -> dict:
    """
    Run ngspice syntax verification on a translated file.
    
    Performs basic syntax check by loading the file into ngspice 
    without instantiating devices. This validates syntax without
    requiring specific device parameters.
    
    Returns dict with 'passed', 'device_name', 'device_type', 'error'
    """
    try:
        content = output_file.read_text()
        
        # Extract first model or subcircuit info for reporting
        model_match = re.search(r'\.model\s+(\S+)\s+(\S+)', content, re.IGNORECASE)
        subckt_match = re.search(r'\.subckt\s+(\S+)', content, re.IGNORECASE)
        
        device_name = None
        device_type = None
        
        if model_match:
            device_name = model_match.group(1)
            model_type = model_match.group(2).lower()
            if 'nmos' in model_type or 'pmos' in model_type:
                device_type = 'mos'
            elif 'npn' in model_type or 'pnp' in model_type:
                device_type = 'bjt'
            elif model_type in ['d', 'diode']:
                device_type = 'diode'
            elif model_type in ['r', 'resistor']:
                device_type = 'resistor'
            elif model_type in ['c', 'capacitor']:
                device_type = 'capacitor'
        elif subckt_match:
            device_name = subckt_match.group(1)
            # Guess type from name
            name_lower = device_name.lower()
            if any(x in name_lower for x in ['nmos', 'pmos', 'mos', 'fet']):
                device_type = 'mos'
            elif any(x in name_lower for x in ['npn', 'pnp', 'bjt']):
                device_type = 'bjt'
            elif any(x in name_lower for x in ['diode', 'dio']):
                device_type = 'diode'
            elif any(x in name_lower for x in ['cap', 'mim']):
                device_type = 'capacitor'
            elif any(x in name_lower for x in ['res']):
                device_type = 'resistor'
        
        if not device_name:
            # File doesn't have recognizable models - do basic syntax check
            device_name = "unknown"
            device_type = "unknown"
        
        # Create a simple syntax verification netlist
        # This includes the file and runs a dummy .op without instantiating devices
        netlist = f"""* ngspice syntax verification
.include '{output_file}'

* Dummy circuit for syntax check (no device instantiation)
V1 test_node 0 DC 1

.op

.control
run
echo VERIFICATION_PASSED
quit
.endc

.end
"""
        
        # Run ngspice
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sp', delete=False) as f:
            f.write(netlist)
            temp_netlist = f.name
        
        try:
            result = subprocess.run(
                ['ngspice', '-b', temp_netlist],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            output = result.stdout + result.stderr
            
            if 'VERIFICATION_PASSED' in output:
                return {
                    'passed': True,
                    'device_name': device_name,
                    'device_type': device_type,
                    'error': None
                }
            else:
                # Check for errors
                error_lines = [l for l in output.split('\n') if 'error' in l.lower()]
                error_msg = error_lines[0] if error_lines else 'ngspice check failed'
                return {
                    'passed': False,
                    'device_name': device_name,
                    'device_type': device_type,
                    'error': error_msg[:200]
                }
        finally:
            Path(temp_netlist).unlink(missing_ok=True)
            
    except Exception as e:
        return {
            'passed': False,
            'error': str(e)[:200]
        }


def generate_plots_for_file(lib_file: Path, max_devices: int = 3) -> dict:
    """
    Generate verification plots for a translated library file.
    
    Args:
        lib_file: Path to the ngspice library file
        max_devices: Maximum number of devices to plot
    
    Returns:
        dict with 'success', 'plot_count', 'plot_dir', 'error'
    """
    try:
        from generate_verification_plots import process_library_file
        
        results = process_library_file(lib_file, max_devices)
        
        if not results:
            return {
                'success': False,
                'plot_count': 0,
                'error': 'No devices found to plot'
            }
        
        # Count total plots
        total_plots = sum(len(plots) for plots in results.values())
        plot_dir = lib_file.parent / 'plots'
        
        return {
            'success': total_plots > 0,
            'plot_count': total_plots,
            'plot_dir': str(plot_dir),
            'error': None
        }
        
    except ImportError as e:
        return {
            'success': False,
            'plot_count': 0,
            'error': f'Could not import plot generator: {e}'
        }
    except Exception as e:
        return {
            'success': False,
            'plot_count': 0,
            'error': str(e)[:200]
        }


def cmd_plot(args):
    """Handle plot command - generate verification plots"""
    path = Path(args.path).resolve()
    
    if not path.exists():
        print(f"❌ Path not found: {path}")
        sys.exit(1)
    
    try:
        from generate_verification_plots import (
            process_library_file, 
            generate_summary_figure
        )
    except ImportError as e:
        print(f"❌ Could not import plot generator: {e}")
        print("   Make sure matplotlib is installed: pip install matplotlib")
        sys.exit(1)
    
    all_results = {}
    
    if path.is_file():
        # Single file
        print(f"📊 Generating plots for: {path.name}")
        results = process_library_file(path, args.max_devices)
        if results:
            all_results[path.stem] = results
    else:
        # Directory - find all .lib files
        lib_files = list(path.rglob("*.lib"))
        lib_files = [f for f in lib_files if 'plots' not in f.parts]
        
        if not lib_files:
            print(f"⚠️ No .lib files found in {path}")
            sys.exit(1)
        
        print(f"📊 Generating plots for {len(lib_files)} library files in: {path}")
        
        for lib_file in sorted(lib_files):
            results = process_library_file(lib_file, args.max_devices)
            if results:
                all_results[lib_file.stem] = results
    
    # Generate summary
    if all_results:
        output_dir = path if path.is_dir() else path.parent
        summary_fig = generate_summary_figure(all_results, output_dir)
        
        total_plots = sum(
            len(plots) 
            for results in all_results.values() 
            for plots in results.values()
        )
        
        print(f"\n✅ Generated {total_plots} verification plots")
        if summary_fig:
            print(f"📊 Summary: {summary_fig}")
    else:
        print("⚠️ No plots were generated")


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
        description='SPICE Translator with Verification and Plotting',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Translate:
    %(prog)s translate input.scs --target ngspice
    %(prog)s translate input.scs --target ngspice --verify
    %(prog)s translate input.scs --target ngspice --verify --plot
    
  Generate Plots:
    %(prog)s plot output/translated.lib
    %(prog)s plot output/cadence90_spectre-ngspice/ --max-devices 2
    
  Verify:
    %(prog)s verify gpdk090_capacitor.scs mimcap --device-class capacitor --area 10e-6
    
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
    translate_parser.add_argument('--verify', '-v', action='store_true',
                                  help='Run ngspice syntax verification after translation')
    translate_parser.add_argument('--plot', '-p', action='store_true',
                                  help='Generate verification plots (ngspice target only)')
    translate_parser.add_argument('--max-plots', type=int, default=3,
                                  help='Max devices to plot per file (default: 3)')
    
    # Plot command
    plot_parser = subparsers.add_parser('plot', help='Generate verification plots for translated files')
    plot_parser.add_argument('path', help='Library file or directory containing .lib files')
    plot_parser.add_argument('--max-devices', '-m', type=int, default=3,
                            help='Max devices to plot per file (default: 3)')
    
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
    elif args.command == 'plot':
        cmd_plot(args)
    elif args.command == 'verify':
        cmd_verify(args)
    elif args.command == 'verify-all':
        cmd_verify_all(args)


if __name__ == '__main__':
    main()
