#!/usr/bin/env python3
"""
Test Results Analyzer

Analyzes test_results/all_files_report.json and generates:
1. Success rate by file size
2. Common error patterns
3. Model type distribution
4. Performance metrics
"""

import json
from pathlib import Path
from collections import defaultdict
import sys

def analyze_results(report_file: Path):
    """Analyze test results and generate report."""
    with open(report_file) as f:
        data = json.load(f)
    
    summary = data['summary']
    files = data['files']
    
    print(f"\n{'='*70}")
    print(f"Test Results Analysis")
    print(f"{'='*70}\n")
    
    # Overall stats
    print(f"Overall Statistics:")
    print(f"  Total Files: {summary['total_files']}")
    print(f"  Success Rate: {summary['success']}/{summary['total_files']} "
          f"({summary['success']/summary['total_files']*100:.1f}%)")
    print(f"  Total Models: {summary['total_models']}")
    print(f"  Avg Time: {summary['avg_time_per_file']:.3f}s per file")
    print()
    
    # Size distribution
    size_buckets = defaultdict(lambda: {'count': 0, 'success': 0})
    for f in files:
        size = f['size_kb']
        if size < 10:
            bucket = '<10KB'
        elif size < 50:
            bucket = '10-50KB'
        elif size < 100:
            bucket = '50-100KB'
        else:
            bucket = '>100KB'
        
        size_buckets[bucket]['count'] += 1
        if f['status'] == 'success':
            size_buckets[bucket]['success'] += 1
    
    print(f"Success Rate by File Size:")
    for bucket in ['<10KB', '10-50KB', '50-100KB', '>100KB']:
        if bucket in size_buckets:
            stats = size_buckets[bucket]
            rate = stats['success'] / stats['count'] * 100
            print(f"  {bucket:12s}: {stats['success']}/{stats['count']} ({rate:.1f}%)")
    print()
    
    # Error analysis
    error_counts = defaultdict(int)
    for f in files:
        for err in f['errors']:
            # Extract error type
            if ':' in err:
                error_type = err.split(':')[0]
            else:
                error_type = err[:50]
            error_counts[error_type] += 1
    
    if error_counts:
        print(f"Most Common Errors:")
        for error_type, count in sorted(error_counts.items(), 
                                       key=lambda x: x[1], 
                                       reverse=True)[:5]:
            print(f"  {count:2d}x: {error_type}")
        print()
    
    # Top performers
    successful = [f for f in files if f['status'] == 'success']
    if successful:
        print(f"Largest Successfully Translated Files:")
        for f in sorted(successful, key=lambda x: x['size_kb'], reverse=True)[:5]:
            print(f"  {f['file']:40s} {f['size_kb']:6.1f} KB, {f['models']:3d} models")
        print()
    
    # Problem files
    failures = [f for f in files if f['status'] in ['failed', 'error']]
    if failures:
        print(f"Problem Files Requiring Attention:")
        for f in failures[:10]:
            print(f"  {f['file']:40s} {f['status']:8s}")
            if f['errors']:
                print(f"    └─ {f['errors'][0][:60]}")
        print()

if __name__ == '__main__':
    report_file = Path(__file__).parent.parent / 'test_results' / 'all_files_report.json'
    if not report_file.exists():
        print(f"Error: Report not found: {report_file}")
        print(f"Run: pytest tests/integration/test_all_real_files.py::test_batch_all_files_with_report")
        sys.exit(1)
    
    analyze_results(report_file)
