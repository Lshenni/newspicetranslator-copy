#!/usr/bin/env python3
"""
Roundtrip Verification Tool

Tests translation quality by:
1. Parse source file (Format A)
2. Translate to Format B
3. Translate back to Format A
4. Compare original vs. final

Reports:
- Model count preservation
- Parameter value differences
- Name/alias changes
- Warnings and errors

Usage:
    python tools/verify_roundtrip.py input.scs --via ngspice
    python tools/verify_roundtrip.py input.lib --via spectre --format hspice
"""

import argparse
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Any
import json
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.parsers import SpectreParser, HSPICEParser, NgspiceParser
from src.writers import SpectreWriter, HSPICEWriter, NgspiceWriter
from src.validation import IRValidator


@dataclass
class RoundtripResult:
    """Results of roundtrip test."""
    success: bool
    source_file: str
    intermediate_format: str
    source_models: int
    intermediate_models: int
    final_models: int
    model_names_preserved: bool
    parameter_diffs: List[Dict[str, Any]]
    warnings: List[str]
    errors: List[str]
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON export."""
        return {
            'success': self.success,
            'source_file': self.source_file,
            'intermediate_format': self.intermediate_format,
            'models': {
                'source': self.source_models,
                'intermediate': self.intermediate_models,
                'final': self.final_models
            },
            'model_names_preserved': self.model_names_preserved,
            'parameter_diffs': self.parameter_diffs,
            'warnings': self.warnings,
            'errors': self.errors
        }
    
    def print_summary(self):
        """Print human-readable summary."""
        print(f"\n{'='*60}")
        print(f"Roundtrip Test: {self.source_file}")
        print(f"{'='*60}")
        print(f"Route: source → {self.intermediate_format} → source")
        print(f"Models: {self.source_models} → {self.intermediate_models} → {self.final_models}")
        
        if self.success:
            print(f"\n✓ SUCCESS: Roundtrip completed")
        else:
            print(f"\n✗ FAILED: {len(self.errors)} errors")
        
        if self.model_names_preserved:
            print(f"✓ Model names preserved")
        else:
            print(f"⚠ Model names changed")
        
        if self.parameter_diffs:
            print(f"\n⚠ Parameter Differences: {len(self.parameter_diffs)}")
            for diff in self.parameter_diffs[:5]:
                print(f"  - {diff['model']}.{diff['parameter']}: "
                      f"{diff['original']} → {diff['final']} "
                      f"(Δ={diff['delta']:.2e})")
            if len(self.parameter_diffs) > 5:
                print(f"  ... and {len(self.parameter_diffs) - 5} more")
        
        if self.warnings:
            print(f"\nWarnings: {len(self.warnings)}")
            for w in self.warnings[:3]:
                print(f"  - {w}")
        
        if self.errors:
            print(f"\nErrors: {len(self.errors)}")
            for e in self.errors[:3]:
                print(f"  - {e}")
        
        print(f"{'='*60}\n")


class RoundtripTester:
    """Performs roundtrip translation tests."""
    
    def __init__(self, tolerance: float = 1e-6):
        self.tolerance = tolerance
    
    def test_roundtrip(
        self,
        source_file: Path,
        source_format: str,
        intermediate_format: str,
        output_dir: Path = None
    ) -> RoundtripResult:
        """
        Perform roundtrip test.
        
        Args:
            source_file: Original file to test
            source_format: Source format (spectre, hspice, ngspice)
            intermediate_format: Intermediate format for translation
            output_dir: Optional directory for intermediate files
        
        Returns:
            RoundtripResult with detailed comparison
        """
        result = RoundtripResult(
            success=False,
            source_file=str(source_file),
            intermediate_format=intermediate_format,
            source_models=0,
            intermediate_models=0,
            final_models=0,
            model_names_preserved=False,
            parameter_diffs=[],
            warnings=[],
            errors=[]
        )
        
        # Use temp dir if not specified
        if output_dir is None:
            output_dir = Path("/tmp/roundtrip_test")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Step 1: Parse original
            source_parser = self._get_parser(source_format, source_file)
            source_models = source_parser.parse_to_ir()
            result.source_models = len(source_models)
            
            # Step 2: Translate to intermediate format
            intermediate_file = output_dir / f"intermediate.{self._get_extension(intermediate_format)}"
            intermediate_writer = self._get_writer(intermediate_format, intermediate_file)
            intermediate_writer.write_from_ir(source_models)
            
            # Step 3: Parse intermediate
            intermediate_parser = self._get_parser(intermediate_format, intermediate_file)
            intermediate_models = intermediate_parser.parse_to_ir()
            result.intermediate_models = len(intermediate_models)
            
            # Step 4: Translate back to source format
            final_file = output_dir / f"final.{self._get_extension(source_format)}"
            final_writer = self._get_writer(source_format, final_file)
            final_writer.write_from_ir(intermediate_models)
            
            # Step 5: Parse final
            final_parser = self._get_parser(source_format, final_file)
            final_models = final_parser.parse_to_ir()
            result.final_models = len(final_models)
            
            # Step 6: Compare
            self._compare_models(source_models, final_models, result)
            
            # Success if no errors
            result.success = len(result.errors) == 0
            
        except Exception as e:
            result.errors.append(f"Roundtrip failed: {str(e)}")
        
        return result
    
    def _compare_models(self, source_models, final_models, result):
        """Compare source and final models, populate result."""
        # Check model count
        if len(source_models) != len(final_models):
            result.errors.append(
                f"Model count mismatch: {len(source_models)} → {len(final_models)}"
            )
            return
        
        # Check model names
        source_names = {m.name for m in source_models}
        final_names = {m.name for m in final_models}
        result.model_names_preserved = (source_names == final_names)
        
        if not result.model_names_preserved:
            missing = source_names - final_names
            added = final_names - source_names
            if missing:
                result.warnings.append(f"Missing models: {missing}")
            if added:
                result.warnings.append(f"Added models: {added}")
        
        # Compare parameters
        for src_model, final_model in zip(source_models, final_models):
            self._compare_parameters(src_model, final_model, result)
    
    def _compare_parameters(self, src_model, final_model, result):
        """Compare parameters between two models."""
        src_params = src_model.base_parameters
        final_params = final_model.base_parameters
        
        # Find parameter differences
        all_keys = set(src_params.keys()) | set(final_params.keys())
        
        for key in all_keys:
            src_val = src_params.get(key)
            final_val = final_params.get(key)
            
            if src_val is None:
                result.warnings.append(
                    f"{final_model.name}: Parameter '{key}' added in final"
                )
            elif final_val is None:
                result.warnings.append(
                    f"{src_model.name}: Parameter '{key}' missing in final"
                )
            else:
                # Compare values
                try:
                    src_float = float(src_val)
                    final_float = float(final_val)
                    delta = abs(src_float - final_float)
                    
                    if delta > self.tolerance:
                        result.parameter_diffs.append({
                            'model': src_model.name,
                            'parameter': key,
                            'original': src_float,
                            'final': final_float,
                            'delta': delta
                        })
                except (ValueError, TypeError):
                    # String comparison
                    if str(src_val) != str(final_val):
                        result.warnings.append(
                            f"{src_model.name}.{key}: '{src_val}' → '{final_val}'"
                        )
    
    def _get_parser(self, format_name: str, file_path: Path):
        """Get parser instance."""
        parsers = {
            'spectre': SpectreParser,
            'hspice': HSPICEParser,
            'ngspice': NgspiceParser
        }
        return parsers[format_name.lower()](file_path)
    
    def _get_writer(self, format_name: str, file_path: Path):
        """Get writer instance."""
        writers = {
            'spectre': SpectreWriter,
            'hspice': HSPICEWriter,
            'ngspice': NgspiceWriter
        }
        return writers[format_name.lower()](file_path)
    
    def _get_extension(self, format_name: str) -> str:
        """Get file extension for format."""
        extensions = {
            'spectre': 'scs',
            'hspice': 'sp',
            'ngspice': 'lib'
        }
        return extensions[format_name.lower()]


def main():
    parser = argparse.ArgumentParser(
        description='Roundtrip translation verification tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Test Spectre → ngspice → Spectre
  python tools/verify_roundtrip.py models.scs --via ngspice
  
  # Test HSPICE → Spectre → HSPICE
  python tools/verify_roundtrip.py models.sp --via spectre --format hspice
  
  # Export results as JSON
  python tools/verify_roundtrip.py models.scs --via ngspice --json results.json
        '''
    )
    
    parser.add_argument('input', help='Input SPICE file')
    parser.add_argument('--via', required=True,
                       choices=['spectre', 'hspice', 'ngspice'],
                       help='Intermediate format for roundtrip')
    parser.add_argument('--format', 
                       choices=['spectre', 'hspice', 'ngspice'],
                       help='Source format (auto-detect if not specified)')
    parser.add_argument('--tolerance', type=float, default=1e-6,
                       help='Tolerance for parameter comparison (default: 1e-6)')
    parser.add_argument('--json', help='Export results as JSON')
    parser.add_argument('--output-dir', help='Directory for intermediate files')
    
    args = parser.parse_args()
    
    # Auto-detect format
    input_file = Path(args.input)
    if not input_file.exists():
        print(f"Error: File not found: {input_file}")
        return 1
    
    if args.format:
        source_format = args.format
    else:
        # Auto-detect from extension
        ext = input_file.suffix.lower()
        ext_map = {'.scs': 'spectre', '.sp': 'hspice', '.lib': 'ngspice'}
        source_format = ext_map.get(ext, 'spectre')
        print(f"Auto-detected format: {source_format}")
    
    # Run roundtrip test
    tester = RoundtripTester(tolerance=args.tolerance)
    output_dir = Path(args.output_dir) if args.output_dir else None
    
    result = tester.test_roundtrip(
        source_file=input_file,
        source_format=source_format,
        intermediate_format=args.via,
        output_dir=output_dir
    )
    
    # Print results
    result.print_summary()
    
    # Export JSON if requested
    if args.json:
        json_path = Path(args.json)
        json_path.write_text(json.dumps(result.to_dict(), indent=2))
        print(f"Results exported to: {json_path}")
    
    return 0 if result.success else 1


if __name__ == '__main__':
    sys.exit(main())
