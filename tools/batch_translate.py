#!/usr/bin/env python3
"""
Batch translation tool with organized output.

Translates multiple SPICE files and organizes outputs by translation type.
"""

import argparse
from pathlib import Path
import json
from typing import List
import time
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.main import TranslationEngine
from src.utils import OutputManager


def batch_translate(
    input_files: List[Path],
    source_format: str,
    target_format: str,
    output_dir: Path = None,
    validate: bool = True,
    continue_on_error: bool = True
) -> dict:
    """
    Translate multiple files with organized output.
    
    Args:
        input_files: List of input files
        source_format: Source format
        target_format: Target format
        output_dir: Base output directory
        validate: Enable validation
        continue_on_error: Continue if a file fails
    
    Returns:
        Dictionary with batch results
    """
    output_manager = OutputManager(base_dir=output_dir)
    engine = TranslationEngine(output_manager=output_manager)
    
    results = {
        'summary': {
            'total_files': len(input_files),
            'successful': 0,
            'failed': 0,
            'total_models': 0,
            'total_time': 0
        },
        'files': []
    }
    
    start_time = time.time()
    
    for input_file in input_files:
        print(f"\nTranslating: {input_file.name}")
        print(f"  {source_format} → {target_format}")
        
        file_result = {
            'input': str(input_file),
            'output': None,
            'status': 'unknown',
            'models': 0,
            'errors': [],
            'time': 0
        }
        
        try:
            file_start = time.time()
            
            # Auto-generate organized output path
            output_file = output_manager.get_output_path(
                input_file,
                source_format,
                target_format
            )
            
            # Translate
            result = engine.translate(
                input_file=input_file,
                output_file=output_file,
                source_format=source_format,
                target_format=target_format,
                validate=validate,
                use_organized_output=True
            )
            
            file_result['time'] = time.time() - file_start
            file_result['output'] = str(output_file)
            
            if result['success']:
                file_result['status'] = 'success'
                file_result['models'] = result['models_translated']
                results['summary']['successful'] += 1
                results['summary']['total_models'] += result['models_translated']
                print(f"  ✓ Success: {result['models_translated']} models in {file_result['time']:.2f}s")
                print(f"  Output: {output_file}")
            else:
                file_result['status'] = 'failed'
                file_result['errors'] = [result.get('error', 'Unknown error')]
                results['summary']['failed'] += 1
                print(f"  ✗ Failed: {result.get('error')}")
                
                if not continue_on_error:
                    break
        
        except Exception as e:
            file_result['status'] = 'error'
            file_result['errors'] = [str(e)]
            results['summary']['failed'] += 1
            print(f"  ✗ Error: {e}")
            
            if not continue_on_error:
                break
        
        results['files'].append(file_result)
    
    results['summary']['total_time'] = time.time() - start_time
    
    # Save report
    report_path = output_manager.get_report_path('batch_translation')
    report_path.write_text(json.dumps(results, indent=2))
    
    # Print summary
    print(f"\n{'='*70}")
    print(f"Batch Translation Complete")
    print(f"{'='*70}")
    print(f"Success: {results['summary']['successful']}/{results['summary']['total_files']}")
    print(f"Failed: {results['summary']['failed']}")
    print(f"Total Models: {results['summary']['total_models']}")
    print(f"Total Time: {results['summary']['total_time']:.2f}s")
    print(f"Report: {report_path}")
    print(f"{'='*70}\n")
    
    return results


def main():
    parser = argparse.ArgumentParser(
        description='Batch SPICE file translation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Translate all .scs files in directory
  python tools/batch_translate.py input/*.scs --from spectre --to ngspice
  
  # Translate with custom output directory
  python tools/batch_translate.py input/*.scs --from spectre --to ngspice \\
      --output-dir /path/to/output
  
  # Stop on first error
  python tools/batch_translate.py input/*.scs --from spectre --to ngspice \\
      --stop-on-error
        '''
    )
    
    parser.add_argument('files', nargs='+', help='Input files to translate')
    parser.add_argument('--from', dest='source_format', required=True,
                       choices=['spectre', 'hspice', 'ngspice'],
                       help='Source format')
    parser.add_argument('--to', dest='target_format', required=True,
                       choices=['spectre', 'hspice', 'ngspice'],
                       help='Target format')
    parser.add_argument('--output-dir', type=Path,
                       help='Base output directory (default: ./output)')
    parser.add_argument('--no-validate', action='store_true',
                       help='Skip validation')
    parser.add_argument('--stop-on-error', action='store_true',
                       help='Stop on first error')
    
    args = parser.parse_args()
    
    # Expand file patterns
    input_files = [Path(f) for f in args.files]
    
    # Run batch translation
    results = batch_translate(
        input_files=input_files,
        source_format=args.source_format,
        target_format=args.target_format,
        output_dir=args.output_dir,
        validate=not args.no_validate,
        continue_on_error=not args.stop_on_error
    )
    
    # Exit code: 0 if all succeeded, 1 if any failed
    return 0 if results['summary']['failed'] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
