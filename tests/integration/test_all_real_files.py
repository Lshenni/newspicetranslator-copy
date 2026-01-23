"""
Comprehensive testing of all 38 real Spectre files.

This extends test_real_files.py to cover ALL available files,
not just the first 5.
"""

import pytest
from pathlib import Path
import json
import time

from tests.integration.test_real_files import (
    find_spectre_files,
    PROJECT_ROOT
)
from src.parsers import SpectreParser
from src.writers import NgspiceWriter, HSPICEWriter
from src.validation import IRValidator, SyntaxValidator, SPICEFormat

# Get ALL files
ALL_SPECTRE_FILES = find_spectre_files()


@pytest.mark.parametrize("input_file", ALL_SPECTRE_FILES)
def test_parse_all_spectre_files(input_file):
    """Parse all 38 Spectre files."""
    parser = SpectreParser(input_file)
    
    try:
        models = parser.parse_to_ir()
        
        # Basic validation
        validator = IRValidator()
        result = validator.validate(models)
        
        # Log results
        print(f"✓ {input_file.name}: {len(models)} models, "
              f"{result.error_count} errors, {result.warning_count} warnings")
        
        assert result.error_count == 0, \
            f"IR errors in {input_file}: {result.errors[:3]}"
    
    except Exception as e:
        pytest.fail(f"Failed to parse {input_file}: {e}")


@pytest.mark.parametrize("input_file", ALL_SPECTRE_FILES)
def test_translate_all_to_ngspice(input_file, tmp_path):
    """Translate all 38 files to ngspice."""
    parser = SpectreParser(input_file)
    models = parser.parse_to_ir()
    
    if len(models) == 0:
        pytest.skip(f"No models in {input_file}")
    
    output_file = tmp_path / f"{input_file.stem}_ngspice.lib"
    writer = NgspiceWriter(output_file)
    
    try:
        writer.write_from_ir(models)
        
        assert output_file.exists()
        assert output_file.stat().st_size > 0
        
        # Validate syntax
        content = output_file.read_text()
        validator = SyntaxValidator(format=SPICEFormat.NGSPICE)
        result = validator.validate(content)
        
        print(f"✓ {input_file.name} → ngspice: {len(models)} models")
        
        assert result.error_count == 0
        
    except Exception as e:
        pytest.fail(f"Translation failed for {input_file}: {e}")


@pytest.mark.parametrize("input_file", ALL_SPECTRE_FILES)
def test_translate_all_to_hspice(input_file, tmp_path):
    """Translate all 38 files to HSPICE."""
    parser = SpectreParser(input_file)
    models = parser.parse_to_ir()
    
    if len(models) == 0:
        pytest.skip(f"No models in {input_file}")
    
    output_file = tmp_path / f"{input_file.stem}_hspice.sp"
    writer = HSPICEWriter(output_file)
    
    try:
        writer.write_from_ir(models)
        
        assert output_file.exists()
        assert output_file.stat().st_size > 0
        
        # Validate syntax
        content = output_file.read_text()
        validator = SyntaxValidator(format=SPICEFormat.HSPICE)
        result = validator.validate(content)
        
        print(f"✓ {input_file.name} → HSPICE: {len(models)} models")
        
        assert result.error_count == 0
        
    except Exception as e:
        pytest.fail(f"Translation failed for {input_file}: {e}")


def test_batch_all_files_with_report(tmp_path):
    """
    Batch test all files and generate detailed report.
    """
    results = []
    start_time = time.time()
    
    for input_file in ALL_SPECTRE_FILES:
        file_result = {
            'file': input_file.name,
            'size_kb': input_file.stat().st_size / 1024,
            'status': 'unknown',
            'models': 0,
            'errors': [],
            'warnings': [],
            'parse_time': 0,
            'translate_time': 0
        }
        
        try:
            # Parse
            parse_start = time.time()
            parser = SpectreParser(input_file)
            models = parser.parse_to_ir()
            file_result['parse_time'] = time.time() - parse_start
            file_result['models'] = len(models)
            
            if len(models) == 0:
                file_result['status'] = 'skipped'
                file_result['warnings'].append('No models found')
                results.append(file_result)
                continue
            
            # Translate
            translate_start = time.time()
            output_file = tmp_path / f"{input_file.stem}.lib"
            writer = NgspiceWriter(output_file)
            writer.write_from_ir(models)
            file_result['translate_time'] = time.time() - translate_start
            
            # Validate
            content = output_file.read_text()
            validator = SyntaxValidator(format=SPICEFormat.NGSPICE)
            result = validator.validate(content)
            
            if result.error_count > 0:
                file_result['status'] = 'failed'
                file_result['errors'] = result.errors[:5]
            else:
                file_result['status'] = 'success'
                if result.warning_count > 0:
                    file_result['warnings'] = result.warnings[:3]
        
        except Exception as e:
            file_result['status'] = 'error'
            file_result['errors'].append(str(e))
        
        results.append(file_result)
    
    total_time = time.time() - start_time
    
    # Generate report
    report = {
        'summary': {
            'total_files': len(ALL_SPECTRE_FILES),
            'success': sum(1 for r in results if r['status'] == 'success'),
            'failed': sum(1 for r in results if r['status'] == 'failed'),
            'errors': sum(1 for r in results if r['status'] == 'error'),
            'skipped': sum(1 for r in results if r['status'] == 'skipped'),
            'total_models': sum(r['models'] for r in results),
            'total_time': total_time,
            'avg_time_per_file': total_time / len(ALL_SPECTRE_FILES) if ALL_SPECTRE_FILES else 0
        },
        'files': results
    }
    
    # Save report
    report_file = PROJECT_ROOT / 'test_results' / 'all_files_report.json'
    report_file.parent.mkdir(exist_ok=True)
    report_file.write_text(json.dumps(report, indent=2))
    
    # Print summary
    print(f"\n{'='*70}")
    print(f"Batch Test Results: ALL {len(ALL_SPECTRE_FILES)} Files")
    print(f"{'='*70}")
    print(f"Success: {report['summary']['success']}/{report['summary']['total_files']}")
    print(f"Failed: {report['summary']['failed']}")
    print(f"Errors: {report['summary']['errors']}")
    print(f"Skipped: {report['summary']['skipped']}")
    print(f"Total Models: {report['summary']['total_models']}")
    print(f"Total Time: {total_time:.2f}s")
    print(f"Report saved: {report_file}")
    print(f"{'='*70}\n")
    
    # Show failures
    if report['summary']['failed'] > 0 or report['summary']['errors'] > 0:
        print("Failed/Error Files:")
        for r in results:
            if r['status'] in ['failed', 'error']:
                print(f"  ✗ {r['file']}: {r['status']}")
                for err in r['errors'][:2]:
                    print(f"      - {err}")
    
    # At least 80% should succeed
    success_rate = report['summary']['success'] / report['summary']['total_files'] if report['summary']['total_files'] > 0 else 0
    assert success_rate >= 0.80, \
        f"Success rate {success_rate:.1%} below 80% threshold"
