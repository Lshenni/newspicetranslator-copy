#!/usr/bin/env python3
"""
Batch Translation Script with Auto-Detection and JSON Summary

Translates all SPICE model files in a folder with:
- Automatic source format detection
- JSON summary with statistics and errors
- Optional verification with plot generation

Usage:
    ./batch_translate.py tools/spice-libraries/private-models/asap7 --target ngspice
    ./batch_translate.py tools/spice-libraries/private-models/smic180HV --target spectre --verify
"""

import sys
import json
import argparse
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict, field
import traceback

# Add project root to path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from src.main import TranslationEngine


@dataclass
class VerificationResult:
    """Result of ngspice verification"""
    verified: bool = False
    passed: Optional[bool] = None
    device_name: Optional[str] = None
    device_type: Optional[str] = None
    data_points: int = 0
    data_file: Optional[str] = None
    error: Optional[str] = None


@dataclass
class FileResult:
    """Result for a single file translation"""
    file: str
    source_format: str
    target_format: str
    success: bool
    models_in: int
    models_out: int
    output_file: Optional[str]
    error: Optional[str]
    duration_ms: float
    verified: bool = False
    verification_passed: Optional[bool] = None
    verification_details: Optional[Dict] = None


@dataclass
class BatchSummary:
    """Summary of batch translation"""
    timestamp: str
    source_folder: str
    target_format: str
    total_files: int
    successful: int
    failed: int
    skipped: int
    total_models_in: int
    total_models_out: int
    success_rate: float
    total_duration_ms: float
    verification_summary: Dict
    results: List[Dict]
    errors: List[Dict]


def detect_format(file_path: Path) -> Optional[str]:
    """
    Auto-detect SPICE format from file extension and content.
    
    Returns: 'spectre', 'hspice', 'ngspice', or None
    """
    suffix = file_path.suffix.lower()
    name_lower = file_path.name.lower()
    
    # Extension-based detection
    if suffix == '.scs':
        return 'spectre'
    elif suffix in ['.mdl', '.mod']:
        return 'hspice'
    elif suffix == '.spice' or name_lower.endswith('.model.spice'):
        # .spice files are typically ngspice format (e.g., sky130, gf180)
        return 'ngspice'
    elif suffix == '.sp':
        return 'ngspice'
    elif suffix == '.lib':
        # .lib can be HSPICE or ngspice - check content
        try:
            content = file_path.read_text(errors='ignore')[:2000]
            
            # Check for Spectre-specific syntax
            if 'simulator lang=spectre' in content.lower():
                return 'spectre'
            
            # Check for ngspice-specific patterns
            if '.subckt' in content.lower() and 'level=14' in content.lower():
                return 'ngspice'
            
            # Default to HSPICE for .lib files
            return 'hspice'
        except Exception:
            return 'hspice'
    
    # Content-based fallback
    try:
        content = file_path.read_text(errors='ignore')[:2000]
        
        if 'simulator lang=spectre' in content.lower():
            return 'spectre'
        elif '.model' in content.lower() or '.subckt' in content.lower():
            return 'hspice'  # Default to HSPICE for generic SPICE
        
    except Exception:
        pass
    
    return None


def verify_ngspice_file(output_file: Path, output_dir: Path) -> VerificationResult:
    """
    Run ngspice syntax verification on translated file.
    
    Performs a basic syntax check by loading the file into ngspice.
    For files with models, attempts a simple DC operating point analysis.
    
    Args:
        output_file: Path to the translated ngspice library file
        output_dir: Directory to save verification data
    
    Returns:
        VerificationResult with verification status
    """
    try:
        # Extract first model/subcircuit name from file
        content = output_file.read_text()
        
        device_name = None
        device_type = None
        
        # Find first .subckt or .model
        for line in content.split('\n'):
            line_lower = line.lower().strip()
            if line_lower.startswith('.subckt '):
                parts = line.split()
                if len(parts) >= 2:
                    device_name = parts[1]
                    # Guess device type from name
                    name_lower = device_name.lower()
                    if 'nmos' in name_lower or 'pmos' in name_lower or 'mos' in name_lower:
                        device_type = 'mos'
                    elif 'npn' in name_lower or 'pnp' in name_lower or 'bjt' in name_lower:
                        device_type = 'bjt'
                    elif 'dio' in name_lower or 'diode' in name_lower:
                        device_type = 'diode'
                    elif 'cap' in name_lower or 'mim' in name_lower:
                        device_type = 'capacitor'
                    elif 'res' in name_lower:
                        device_type = 'resistor'
                    break
            elif line_lower.startswith('.model '):
                parts = line.split()
                if len(parts) >= 3:
                    device_name = parts[1]
                    model_type = parts[2].lower()
                    if model_type in ['nmos', 'pmos']:
                        device_type = 'mos'
                    elif model_type in ['npn', 'pnp']:
                        device_type = 'bjt'
                    elif model_type == 'd':
                        device_type = 'diode'
                    elif model_type == 'r':
                        device_type = 'resistor'
                    elif model_type == 'c':
                        device_type = 'capacitor'
                    break
        
        if not device_name:
            return VerificationResult(
                verified=True,
                passed=True,
                error="No models found to verify (empty file)"
            )
        
        # Create a simple verification netlist
        data_file = output_dir / f"{output_file.stem}_verify.csv"
        
        # Basic syntax verification netlist
        netlist = f"""* Syntax Verification Test
.include "{output_file}"

* Dummy circuit for syntax check
V1 test_node 0 DC 1

.op

.control
run
echo "VERIFICATION_PASSED"
quit
.endc

.end
"""
        
        # Write and run netlist
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sp', delete=False) as f:
            f.write(netlist)
            netlist_file = f.name
        
        try:
            result = subprocess.run(
                ['ngspice', '-b', netlist_file],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Check if verification passed
            passed = 'VERIFICATION_PASSED' in result.stdout
            has_errors = 'Error' in result.stderr or 'error' in result.stderr.lower()
            
            # Clean up
            Path(netlist_file).unlink(missing_ok=True)
            
            if passed and not has_errors:
                return VerificationResult(
                    verified=True,
                    passed=True,
                    device_name=device_name,
                    device_type=device_type,
                    data_file=str(data_file) if data_file.exists() else None
                )
            else:
                # Extract error message
                error_lines = [l for l in result.stderr.split('\n') if 'error' in l.lower()]
                error_msg = error_lines[0] if error_lines else "Simulation failed"
                
                return VerificationResult(
                    verified=True,
                    passed=False,
                    device_name=device_name,
                    device_type=device_type,
                    error=error_msg[:200]
                )
                
        except subprocess.TimeoutExpired:
            Path(netlist_file).unlink(missing_ok=True)
            return VerificationResult(
                verified=True,
                passed=False,
                device_name=device_name,
                error="Verification timed out (30s)"
            )
            
    except Exception as e:
        return VerificationResult(
            verified=True,
            passed=False,
            error=str(e)[:200]
        )


def get_output_extension(target_format: str) -> str:
    """Get output file extension for target format"""
    if target_format == 'spectre':
        return '.scs'
    else:
        return '.lib'


def translate_file(
    engine: TranslationEngine,
    input_file: Path,
    output_dir: Path,
    source_format: str,
    target_format: str
) -> FileResult:
    """Translate a single file and return result"""
    import time
    
    start_time = time.time()
    
    # Create output file path
    ext = get_output_extension(target_format)
    output_file = output_dir / input_file.with_suffix(ext).name
    
    try:
        result = engine.translate(
            input_file=input_file,
            output_file=output_file,
            source_format=source_format,
            target_format=target_format
        )
        
        duration_ms = (time.time() - start_time) * 1000
        
        if result.get('success'):
            return FileResult(
                file=str(input_file),
                source_format=source_format,
                target_format=target_format,
                success=True,
                models_in=result.get('models_parsed', 0),
                models_out=result.get('models_translated', 0),
                output_file=str(output_file),
                error=None,
                duration_ms=duration_ms
            )
        else:
            return FileResult(
                file=str(input_file),
                source_format=source_format,
                target_format=target_format,
                success=False,
                models_in=0,
                models_out=0,
                output_file=None,
                error=result.get('error', 'Unknown error'),
                duration_ms=duration_ms
            )
            
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        return FileResult(
            file=str(input_file),
            source_format=source_format,
            target_format=target_format,
            success=False,
            models_in=0,
            models_out=0,
            output_file=None,
            error=str(e),
            duration_ms=duration_ms
        )


def batch_translate(
    source_folder: Path,
    target_format: str,
    output_base: Optional[Path] = None,
    source_format: Optional[str] = None,
    verify: bool = False,
    verbose: bool = False
) -> BatchSummary:
    """
    Batch translate all SPICE files in a folder.
    
    Args:
        source_folder: Folder containing SPICE files
        target_format: Target format ('ngspice', 'hspice', 'spectre')
        output_base: Base output directory (default: ./output)
        source_format: Force source format (default: auto-detect)
        verify: Run verification after translation
        verbose: Print progress
    
    Returns:
        BatchSummary with all results
    """
    import time
    
    start_time = time.time()
    
    # Find all SPICE files
    extensions = ['*.scs', '*.lib', '*.mdl', '*.mod', '*.sp', '*.spice', '*.l']
    files: List[Path] = []
    for ext in extensions:
        files.extend(source_folder.rglob(ext))
    
    # Remove duplicates and sort
    files = sorted(set(files))
    
    if not files:
        print(f"⚠️  No SPICE files found in {source_folder}")
        return BatchSummary(
            timestamp=datetime.now().isoformat(),
            source_folder=str(source_folder),
            target_format=target_format,
            total_files=0,
            successful=0,
            failed=0,
            skipped=0,
            total_models_in=0,
            total_models_out=0,
            success_rate=0.0,
            total_duration_ms=0.0,
            verification_summary={
                'enabled': False,
                'verified_count': 0,
                'passed_count': 0,
                'failed_count': 0,
                'pass_rate': 0.0
            },
            results=[],
            errors=[]
        )
    
    # Setup output directory
    folder_name = source_folder.name
    if output_base is None:
        output_base = BASE_DIR / 'output'
    
    # Create engine
    engine = TranslationEngine()
    
    results: List[FileResult] = []
    errors: List[Dict] = []
    skipped = 0
    
    if verbose:
        print(f"\n🔄 Batch translating {len(files)} files from {source_folder}")
        print(f"   Target format: {target_format}")
        print("="*70)
    
    for i, file in enumerate(files, 1):
        # Detect or use forced source format
        detected = source_format or detect_format(file)
        
        if detected is None:
            if verbose:
                print(f"   [{i}/{len(files)}] ⏭️  {file.name} - Unknown format, skipping")
            skipped += 1
            continue
        
        if detected == target_format:
            if verbose:
                print(f"   [{i}/{len(files)}] ⏭️  {file.name} - Same as target, skipping")
            skipped += 1
            continue
        
        # Create output directory with format info
        output_folder = f"{folder_name}_{detected}-{target_format}"
        output_dir = output_base / output_folder
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Translate
        result = translate_file(engine, file, output_dir, detected, target_format)
        
        # Run verification if requested and translation succeeded
        if verify and result.success and target_format == 'ngspice' and result.output_file:
            verify_result = verify_ngspice_file(Path(result.output_file), output_dir)
            result.verified = verify_result.verified
            result.verification_passed = verify_result.passed
            result.verification_details = {
                'device_name': verify_result.device_name,
                'device_type': verify_result.device_type,
                'data_file': verify_result.data_file,
                'error': verify_result.error
            }
        
        results.append(result)
        
        if result.success:
            if verbose:
                status = "✅"
                verify_status = ""
                if verify and result.verified:
                    verify_status = " ✓" if result.verification_passed else " ✗"
                print(f"   [{i}/{len(files)}] {status} {file.name} - {result.models_out} models{verify_status}")
        else:
            if verbose:
                print(f"   [{i}/{len(files)}] ❌ {file.name} - {result.error}")
            errors.append({
                'file': str(file),
                'error': result.error
            })
    
    total_duration_ms = (time.time() - start_time) * 1000
    
    # Calculate summary
    successful = sum(1 for r in results if r.success)
    failed = sum(1 for r in results if not r.success)
    total_models_in = sum(r.models_in for r in results)
    total_models_out = sum(r.models_out for r in results)
    success_rate = (successful / len(results) * 100) if results else 0.0
    
    # Verification stats
    verified_count = sum(1 for r in results if r.verified)
    verification_passed_count = sum(1 for r in results if r.verification_passed)
    verification_failed_count = sum(1 for r in results if r.verified and not r.verification_passed)
    verification_pass_rate = (verification_passed_count / verified_count * 100) if verified_count > 0 else 0.0
    
    # Build verification summary with detailed results
    verification_summary = {
        'enabled': verify,
        'verified_count': verified_count,
        'passed_count': verification_passed_count,
        'failed_count': verification_failed_count,
        'pass_rate': verification_pass_rate,
        'details': [
            {
                'file': r.file,
                'device_name': r.verification_details.get('device_name') if r.verification_details else None,
                'device_type': r.verification_details.get('device_type') if r.verification_details else None,
                'passed': r.verification_passed,
                'error': r.verification_details.get('error') if r.verification_details else None
            }
            for r in results if r.verified
        ]
    }
    
    summary = BatchSummary(
        timestamp=datetime.now().isoformat(),
        source_folder=str(source_folder),
        target_format=target_format,
        total_files=len(files),
        successful=successful,
        failed=failed,
        skipped=skipped,
        total_models_in=total_models_in,
        total_models_out=total_models_out,
        success_rate=success_rate,
        total_duration_ms=total_duration_ms,
        verification_summary=verification_summary,
        results=[asdict(r) for r in results],
        errors=errors
    )
    
    if verbose:
        print("="*70)
        print(f"\n📊 SUMMARY")
        print(f"   Total files:     {len(files)}")
        print(f"   Successful:      {successful}")
        print(f"   Failed:          {failed}")
        print(f"   Skipped:         {skipped}")
        print(f"   Models in:       {total_models_in}")
        print(f"   Models out:      {total_models_out}")
        print(f"   Success rate:    {success_rate:.1f}%")
        if verify:
            print(f"   Verified:        {verification_summary['verified_count']}")
            print(f"   Verify passed:   {verification_summary['passed_count']}")
            print(f"   Verify failed:   {verification_summary['failed_count']}")
            print(f"   Verify rate:     {verification_summary['pass_rate']:.1f}%")
        print(f"   Duration:        {total_duration_ms:.0f}ms")
    
    return summary


def main():
    parser = argparse.ArgumentParser(
        description='Batch translate SPICE files with auto-detection',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Translate all files in asap7 folder to ngspice
    %(prog)s tools/spice-libraries/private-models/asap7 --target ngspice

    # With verification (syntax check)
    %(prog)s input_folder --target ngspice --verify

    # With verification AND plot generation
    %(prog)s input_folder --target ngspice --plot

    # Limit devices to plot per file
    %(prog)s input_folder --target ngspice --plot --max-plots 2

    # Force source format
    %(prog)s input_folder --target spectre --source hspice

    # Custom output directory
    %(prog)s input_folder --target ngspice --output my_output/

    # Quiet mode with JSON output
    %(prog)s input_folder --target ngspice --quiet --json results.json
        """
    )
    
    parser.add_argument('source_folder', type=Path, 
                        help='Folder containing SPICE files')
    parser.add_argument('--target', '-t', required=True,
                        choices=['ngspice', 'hspice', 'spectre'],
                        help='Target format')
    parser.add_argument('--source', '-s',
                        choices=['ngspice', 'hspice', 'spectre'],
                        help='Force source format (default: auto-detect)')
    parser.add_argument('--output', '-o', type=Path,
                        help='Output base directory')
    parser.add_argument('--verify', '-v', action='store_true',
                        help='Run verification after translation')
    parser.add_argument('--plot', '-p', action='store_true',
                        help='Generate verification plots (implies --verify)')
    parser.add_argument('--max-plots', type=int, default=3,
                        help='Max devices to plot per library file (default: 3)')
    parser.add_argument('--quiet', '-q', action='store_true',
                        help='Suppress progress output')
    parser.add_argument('--json', '-j', type=Path,
                        help='Output JSON summary file (default: output/<folder>_summary.json)')
    
    args = parser.parse_args()
    
    if not args.source_folder.exists():
        print(f"❌ Source folder not found: {args.source_folder}")
        sys.exit(1)
    
    # --plot implies --verify
    verify = args.verify or args.plot
    
    # Run batch translation
    summary = batch_translate(
        source_folder=args.source_folder,
        target_format=args.target,
        output_base=args.output,
        source_format=args.source,
        verify=verify,
        verbose=not args.quiet
    )
    
    # Generate verification plots if requested
    if args.plot and args.target == 'ngspice':
        output_base = args.output or (BASE_DIR / 'output')
        output_folder = f"{args.source_folder.name}_{summary.results[0]['source_format'] if summary.results else 'unknown'}-ngspice"
        output_dir = output_base / output_folder
        
        if output_dir.exists():
            if not args.quiet:
                print(f"\n📊 Generating verification plots...")
            
            try:
                from generate_verification_plots import process_library_file, generate_summary_figure
                
                all_results = {}
                lib_files = list(output_dir.glob("*.lib"))
                
                for lib_file in lib_files:
                    if 'plots' not in lib_file.parts:
                        results = process_library_file(lib_file, args.max_plots)
                        if results:
                            all_results[lib_file.stem] = results
                
                if all_results:
                    summary_fig = generate_summary_figure(all_results, output_dir)
                    total_plots = sum(
                        len(plots) 
                        for results in all_results.values() 
                        for plots in results.values()
                    )
                    if not args.quiet:
                        print(f"   Generated {total_plots} verification plots")
                        if summary_fig:
                            print(f"   Summary: {summary_fig}")
                            
            except ImportError as e:
                if not args.quiet:
                    print(f"   ⚠️ Could not import plot generator: {e}")
            except Exception as e:
                if not args.quiet:
                    print(f"   ⚠️ Plot generation error: {e}")
    
    # Write JSON summary
    if args.json:
        json_file = args.json
    else:
        output_base = args.output or (BASE_DIR / 'output')
        json_file = output_base / f"{args.source_folder.name}_summary.json"
    
    json_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(json_file, 'w') as f:
        json.dump(asdict(summary), f, indent=2)
    
    print(f"\n📄 Summary saved to: {json_file}")
    
    # Exit with error code if any failures
    if summary.failed > 0:
        sys.exit(1)


if __name__ == '__main__':
    main()
