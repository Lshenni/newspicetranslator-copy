#!/usr/bin/env python3
"""
Smart Batch Translation for All PDKs

Automatically detects source format for each PDK and translates to the other
two SPICE formats. Generates verification plots ONLY for ngspice outputs.

PDK Format Mapping:
- sky130, gf180: ngspice format (.spice) → translate to hspice + spectre
- cadence14/45/90/180: spectre format (.scs) → translate to hspice + ngspice
- asap7, synopsys*, smic*, hlmc*, freepdk*: hspice format (.lib) → translate to spectre + ngspice

Usage:
    ./batch_translate_all.py                           # Process all PDKs
    ./batch_translate_all.py --pdk asap7 --pdk smic180 # Process specific PDKs
    ./batch_translate_all.py --no-plots                # Skip plot generation
"""

import sys
import json
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import traceback

# Add project root to path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from src.main import TranslationEngine

# PDK format configuration - maps PDK name patterns to source format
PDK_FORMAT_MAP = {
    # ngspice format PDKs (translate to hspice + spectre)
    'sky130': 'ngspice',
    'gf180': 'ngspice',
    
    # Spectre format PDKs (translate to hspice + ngspice)
    'cadence14': 'spectre',
    'cadence45': 'spectre',
    'cadence90': 'spectre',
    'cadence180': 'spectre',
    
    # HSPICE format PDKs (translate to spectre + ngspice)
    'asap7': 'hspice',
    'synopsys14': 'hspice',
    'synopsys28': 'hspice',
    'smic180': 'hspice',
    'smic180HV': 'hspice',
    'hlmc40lp': 'hspice',
    'hlmc55lp': 'hspice',
    'freepdk15': 'hspice',
    'freepdk3': 'hspice',
    'freepdk45': 'hspice',
    'tsmc65lp': 'hspice',
}

# File extensions for each format
FORMAT_EXTENSIONS = {
    'ngspice': ['*.spice', '*.sp', '*.model.spice'],
    'spectre': ['*.scs'],
    'hspice': ['*.lib', '*.mdl', '*.mod', '*.l'],
}

# Output extensions
OUTPUT_EXTENSIONS = {
    'ngspice': '.lib',
    'hspice': '.lib', 
    'spectre': '.scs',
}


def file_uses_includes(file_path: Path) -> bool:
    """Detect whether a source file relies on include/lib indirection.

    FreePDK45 and HLMC55LP-style wrappers often contain only .include/.lib
    directives and require recursive include resolution to expose the actual
    model cards.
    """
    try:
        content = file_path.read_text(errors='ignore')
    except Exception:
        return False

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith(('*', '//', ';', '#')):
            continue

        lower = line.lower()
        if lower.startswith('.include') or lower.startswith('.inc'):
            return True

        if lower.startswith('.lib'):
            # .lib 'file' section_name  /  .lib section_name
            # Wrapper-style files with quoted paths need include resolution.
            if "'" in line or '"' in line:
                return True

    return False


def get_pdk_source_format(pdk_name: str) -> str:
    """Get the source format for a PDK based on configuration"""
    # Check exact match first
    if pdk_name in PDK_FORMAT_MAP:
        return PDK_FORMAT_MAP[pdk_name]
    
    # Check prefix matches
    for pattern, fmt in PDK_FORMAT_MAP.items():
        if pdk_name.lower().startswith(pattern.lower()):
            return fmt
    
    # Default to hspice
    return 'hspice'


def get_target_formats(source_format: str) -> List[str]:
    """Get the two target formats given a source format"""
    all_formats = ['ngspice', 'hspice', 'spectre']
    return [f for f in all_formats if f != source_format]


def find_spice_files(folder: Path, source_format: str) -> List[Path]:
    """Find SPICE files matching the source format in a folder"""
    extensions = FORMAT_EXTENSIONS.get(source_format, ['*.lib'])
    suffixes = tuple(ext.replace('*', '').lower() for ext in extensions)

    files = []
    for path in folder.rglob('*'):
        if path.is_file() and path.name.lower().endswith(suffixes):
            files.append(path)

    return sorted(set(files))


def translate_file(
    engine: TranslationEngine,
    input_file: Path,
    output_dir: Path,
    source_format: str,
    target_format: str,
    verbose: bool = False,
    follow_includes: bool = False
) -> Dict:
    """Translate a single file"""
    import time
    start_time = time.time()

    effective_follow_includes = follow_includes or file_uses_includes(input_file)
    
    # Create output file path
    ext = OUTPUT_EXTENSIONS.get(target_format, '.lib')
    output_file = output_dir / input_file.with_suffix(ext).name
    
    try:
        result = engine.translate(
            input_file=input_file,
            output_file=output_file,
            source_format=source_format,
            target_format=target_format,
            follow_includes=effective_follow_includes
        )
        
        duration_ms = (time.time() - start_time) * 1000
        
        if result.get('success'):
            return {
                'file': str(input_file),
                'output_file': str(output_file),
                'source_format': source_format,
                'target_format': target_format,
                'success': True,
                'models_out': result.get('models_translated', 0),
                'error': None,
                'duration_ms': duration_ms
            }
        else:
            return {
                'file': str(input_file),
                'output_file': None,
                'source_format': source_format,
                'target_format': target_format,
                'success': False,
                'models_out': 0,
                'error': result.get('error', 'Unknown error'),
                'duration_ms': duration_ms
            }
    except Exception as e:
        return {
            'file': str(input_file),
            'output_file': None,
            'source_format': source_format,
            'target_format': target_format,
            'success': False,
            'models_out': 0,
            'error': str(e),
            'duration_ms': (time.time() - start_time) * 1000
        }


def generate_plots_for_output(output_dir: Path, max_plots: int = 2, verbose: bool = True) -> int:
    """Generate verification plots for ngspice output files"""
    try:
        from generate_verification_plots import process_library_file, generate_summary_figure
        
        lib_files = [f for f in output_dir.glob("*.lib") if 'plots' not in str(f)]
        
        if not lib_files:
            return 0
        
        all_results = {}
        total_plots = 0
        
        for lib_file in lib_files:
            if verbose:
                print(f"\n📂 Processing: {lib_file.name}")
            
            results = process_library_file(lib_file, max_plots)
            if results:
                all_results[lib_file.stem] = results
                file_plots = sum(len(plots) for plots in results.values())
                total_plots += file_plots
        
        # Generate summary figure
        if all_results:
            generate_summary_figure(all_results, output_dir)
        
        return total_plots
        
    except ImportError as e:
        if verbose:
            print(f"   ⚠️ Could not import plot generator: {e}")
        return 0
    except Exception as e:
        if verbose:
            print(f"   ⚠️ Plot generation error: {e}")
        return 0


def process_pdk(
    pdk_folder: Path,
    output_base: Path,
    max_plots: int = 2,
    generate_plots: bool = True,
    verbose: bool = True,
    follow_includes: bool = False
) -> Dict:
    """
    Process a single PDK: detect format and translate to other two formats.
    Generate plots only for ngspice translations.
    """
    pdk_name = pdk_folder.name
    source_format = get_pdk_source_format(pdk_name)
    target_formats = get_target_formats(source_format)
    
    if verbose:
        print(f"\n{'='*70}")
        print(f"📦 PDK: {pdk_name}")
        print(f"   Source format: {source_format}")
        print(f"   Targets: {', '.join(target_formats)}")
        print('='*70)
    
    # Find source files
    files = find_spice_files(pdk_folder, source_format)
    
    if not files:
        if verbose:
            print(f"   ⚠️ No {source_format} files found")
        return {
            'pdk': pdk_name,
            'source_format': source_format,
            'total_files': 0,
            'targets': {}
        }
    
    if verbose:
        print(f"   Found {len(files)} source files")
    
    # Create translation engine
    engine = TranslationEngine()
    
    pdk_results = {
        'pdk': pdk_name,
        'source_format': source_format,
        'total_files': len(files),
        'targets': {}
    }
    
    for target_format in target_formats:
        if verbose:
            print(f"\n   → Translating to {target_format}...")
        
        # Output directory
        output_dir = output_base / f"{pdk_name}_{source_format}-{target_format}"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        target_results = {
            'format': target_format,
            'successful': 0,
            'failed': 0,
            'models_out': 0,
            'plots_generated': 0,
            'errors': [],
            'files': []
        }
        
        for file in files:
            result = translate_file(engine, file, output_dir, source_format, target_format, verbose, follow_includes)
            target_results['files'].append(result)
            
            if result['success']:
                target_results['successful'] += 1
                target_results['models_out'] += result['models_out']
                if verbose:
                    print(f"      ✅ {file.name} → {result['models_out']} models")
            else:
                target_results['failed'] += 1
                target_results['errors'].append({
                    'file': file.name,
                    'error': result['error']
                })
                if verbose:
                    # Suppress verbose output for common errors
                    if 'Invalid models' not in result['error']:
                        print(f"      ❌ {file.name}: {result['error'][:60]}")
        
        # Generate plots ONLY for ngspice translations
        if generate_plots and target_format == 'ngspice' and target_results['successful'] > 0:
            if verbose:
                print(f"\n   📊 Generating verification plots for ngspice output...")
            plots = generate_plots_for_output(output_dir, max_plots, verbose)
            target_results['plots_generated'] = plots
            if verbose:
                print(f"   Generated {plots} plots")
        
        pdk_results['targets'][target_format] = target_results
        
        if verbose:
            success_rate = (target_results['successful'] / len(files) * 100) if files else 0
            print(f"\n   📊 {target_format}: {target_results['successful']}/{len(files)} ({success_rate:.0f}%), {target_results['models_out']} models")
    
    return pdk_results


def main():
    parser = argparse.ArgumentParser(
        description='Smart batch translation for all PDKs',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--pdk', action='append', dest='pdks',
                        help='Specific PDK(s) to process (can be repeated)')
    parser.add_argument('--output', '-o', type=Path, default=Path('output'),
                        help='Output base directory (default: output)')
    parser.add_argument('--max-plots', type=int, default=2,
                        help='Max devices to plot per library file (default: 2)')
    parser.add_argument('--no-plots', action='store_true',
                        help='Skip plot generation')
    parser.add_argument('--follow-includes', '-I', action='store_true',
                        help='Resolve .include/.lib directives (for corner files)')
    parser.add_argument('--quiet', '-q', action='store_true',
                        help='Suppress detailed output')
    parser.add_argument('--json', '-j', type=Path,
                        help='Output JSON results file')
    
    args = parser.parse_args()
    
    # Find all PDK folders
    pdk_base = BASE_DIR / 'tools' / 'spice-libraries' / 'private-models'
    
    if args.pdks:
        pdk_folders = [pdk_base / pdk for pdk in args.pdks if (pdk_base / pdk).exists()]
    else:
        pdk_folders = sorted([f for f in pdk_base.iterdir() if f.is_dir()])
    
    if not pdk_folders:
        print("❌ No PDK folders found")
        sys.exit(1)
    
    print(f"\n🚀 Smart Batch Translation")
    print(f"   Processing {len(pdk_folders)} PDKs")
    print(f"   Output: {args.output}")
    print(f"   Plots: {'disabled' if args.no_plots else f'enabled (max {args.max_plots} per file)'}")
    
    all_results = {
        'timestamp': datetime.now().isoformat(),
        'pdks_processed': len(pdk_folders),
        'results': []
    }
    
    total_success = 0
    total_files = 0
    total_models = 0
    total_plots = 0
    
    for pdk_folder in pdk_folders:
        try:
            result = process_pdk(
                pdk_folder=pdk_folder,
                output_base=args.output,
                max_plots=args.max_plots,
                generate_plots=not args.no_plots,
                verbose=not args.quiet,
                follow_includes=getattr(args, 'follow_includes', False)
            )
            all_results['results'].append(result)
            
            # Accumulate stats
            total_files += result['total_files']
            for target, data in result.get('targets', {}).items():
                total_success += data.get('successful', 0)
                total_models += data.get('models_out', 0)
                total_plots += data.get('plots_generated', 0)
                
        except Exception as e:
            print(f"\n❌ Error processing {pdk_folder.name}: {e}")
            traceback.print_exc()
    
    # Summary
    print(f"\n{'='*70}")
    print(f"📊 FINAL SUMMARY")
    print(f"{'='*70}")
    print(f"   PDKs processed:     {len(pdk_folders)}")
    print(f"   Source files:       {total_files}")
    print(f"   Translations:       {total_success}")
    print(f"   Models translated:  {total_models}")
    print(f"   Plots generated:    {total_plots}")
    
    all_results['summary'] = {
        'total_files': total_files,
        'total_translations': total_success,
        'total_models': total_models,
        'total_plots': total_plots
    }
    
    # Save JSON if requested
    json_file = args.json or (args.output / 'batch_all_summary.json')
    json_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(json_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\n📄 Results saved to: {json_file}")


if __name__ == '__main__':
    main()
