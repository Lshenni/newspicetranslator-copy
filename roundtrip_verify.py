#!/usr/bin/env python3
"""
Round-Trip Translation Verification

Verifies translation accuracy by performing round-trip translation:
  Source → Target → Source
Then comparing the parameter values to detect any translation loss.

Usage:
    python roundtrip_verify.py tools/spice-libraries/private-models/cadence90/spectre/gpdk090_mos.scs
    python roundtrip_verify.py --all
"""

import sys
import re
import json
import argparse
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from src.main import TranslationEngine


@dataclass
class ParameterComparison:
    """Result of comparing a single parameter"""
    param_name: str
    original_value: float
    roundtrip_value: float
    relative_error: float
    matched: bool


@dataclass
class ModelComparison:
    """Result of comparing a single model"""
    model_name: str
    total_params: int
    matched_params: int
    mismatched: List[ParameterComparison]
    missing: List[str]
    extra: List[str]


@dataclass
class RoundtripResult:
    """Complete round-trip verification result"""
    source_file: str
    source_format: str
    intermediate_format: str
    translation1_success: bool
    translation2_success: bool
    total_models: int
    models_matched: int
    total_params: int
    params_matched: int
    match_rate: float
    model_comparisons: List[ModelComparison]
    errors: List[str]


def extract_parameters_from_file(filepath: Path) -> Dict[str, Dict[str, float]]:
    """
    Extract all model parameters from a SPICE library file.
    
    Returns dict of model_name -> {param_name: value}
    """
    content = filepath.read_text()
    models = {}
    
    # Handle ngspice/HSPICE .model format
    # Match: .model name type (params...)
    model_pattern = r'\.model\s+(\S+)\s+\S+\s*\(([^)]+)\)'
    
    for match in re.finditer(model_pattern, content, re.IGNORECASE | re.DOTALL):
        model_name = match.group(1).lower()  # Normalize to lowercase
        param_text = match.group(2)
        
        # Clean up the parameter text (handle line continuations)
        param_text = re.sub(r'\+\s*', ' ', param_text)
        param_text = re.sub(r'\s+', ' ', param_text)
        
        params = {}
        
        # Extract simple numeric parameters: name=value
        # Match: name = number (with optional exponent)
        simple_pattern = r'(\w+)\s*=\s*([+-]?\d+\.?\d*(?:[eE][+-]?\d+)?)'
        
        for pmatch in re.finditer(simple_pattern, param_text):
            pname = pmatch.group(1).lower()
            try:
                pvalue = float(pmatch.group(2))
                params[pname] = pvalue
            except ValueError:
                continue
        
        if params:
            models[model_name] = params
    
    return models


def extract_parameters_from_spectre(filepath: Path) -> Dict[str, Dict[str, float]]:
    """Extract parameters from Spectre format"""
    content = filepath.read_text()
    models = {}
    
    # Spectre model syntax varies - simplified extraction
    # Looking for: model name type (params) or inline subckt
    
    # Simple model statement
    model_pattern = r'model\s+(\S+)\s+\S+\s+([^{]+)'
    
    for match in re.finditer(model_pattern, content, re.IGNORECASE):
        model_name = match.group(1).lower()
        param_text = match.group(2)
        
        params = {}
        simple_pattern = r'(\w+)\s*=\s*([+-]?\d+\.?\d*(?:[eE][+-]?\d+)?)'
        
        for pmatch in re.finditer(simple_pattern, param_text):
            pname = pmatch.group(1).lower()
            try:
                pvalue = float(pmatch.group(2))
                params[pname] = pvalue
            except ValueError:
                continue
        
        if params:
            models[model_name] = params
    
    return models


def compare_models(original: Dict[str, Dict[str, float]], 
                   roundtrip: Dict[str, Dict[str, float]],
                   tolerance: float = 0.001) -> List[ModelComparison]:
    """
    Compare parameter values between original and roundtrip.
    
    Args:
        original: Original model parameters
        roundtrip: Round-trip translated parameters
        tolerance: Relative tolerance for matching (default 0.1%)
    
    Returns:
        List of ModelComparison results
    """
    comparisons = []
    
    for model_name, orig_params in original.items():
        rt_params = roundtrip.get(model_name, {})
        
        mismatched = []
        missing = []
        extra = []
        matched = 0
        
        for pname, pvalue in orig_params.items():
            if pname in rt_params:
                rt_value = rt_params[pname]
                
                # Calculate relative error
                if abs(pvalue) > 1e-30:
                    rel_error = abs(pvalue - rt_value) / abs(pvalue)
                else:
                    rel_error = abs(rt_value)  # Compare to absolute for very small values
                
                if rel_error <= tolerance:
                    matched += 1
                else:
                    mismatched.append(ParameterComparison(
                        param_name=pname,
                        original_value=pvalue,
                        roundtrip_value=rt_value,
                        relative_error=rel_error,
                        matched=False
                    ))
            else:
                missing.append(pname)
        
        # Check for extra parameters in roundtrip
        for pname in rt_params:
            if pname not in orig_params:
                extra.append(pname)
        
        comparisons.append(ModelComparison(
            model_name=model_name,
            total_params=len(orig_params),
            matched_params=matched,
            mismatched=mismatched,
            missing=missing,
            extra=extra
        ))
    
    return comparisons


def run_roundtrip_verification(source_file: Path, 
                                source_format: str = None) -> RoundtripResult:
    """
    Run round-trip translation verification.
    
    Source → Intermediate (ngspice) → Source
    """
    engine = TranslationEngine()
    errors = []
    
    # Auto-detect source format
    if source_format is None:
        if source_file.suffix in ['.scs', '.spectre']:
            source_format = 'spectre'
        elif source_file.suffix in ['.sp', '.hsp', '.hspice']:
            source_format = 'hspice'
        else:
            source_format = 'hspice'  # Default
    
    # Determine intermediate format
    intermediate_format = 'ngspice'
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Step 1: Source → Intermediate
        intermediate_file = tmpdir / "intermediate.lib"
        
        try:
            result1 = engine.translate(
                input_file=source_file,
                source_format=source_format,
                target_format=intermediate_format,
                output_file=intermediate_file
            )
            
            if not result1.get('success'):
                errors.append(f"First translation failed: {result1.get('error', 'Unknown error')}")
                return RoundtripResult(
                    source_file=str(source_file),
                    source_format=source_format,
                    intermediate_format=intermediate_format,
                    translation1_success=False,
                    translation2_success=False,
                    total_models=0,
                    models_matched=0,
                    total_params=0,
                    params_matched=0,
                    match_rate=0.0,
                    model_comparisons=[],
                    errors=errors
                )
        except Exception as e:
            errors.append(f"First translation exception: {str(e)}")
            return RoundtripResult(
                source_file=str(source_file),
                source_format=source_format,
                intermediate_format=intermediate_format,
                translation1_success=False,
                translation2_success=False,
                total_models=0,
                models_matched=0,
                total_params=0,
                params_matched=0,
                match_rate=0.0,
                model_comparisons=[],
                errors=errors
            )
        
        # Step 2: Intermediate → Source format
        roundtrip_file = tmpdir / "roundtrip.lib"
        
        try:
            result2 = engine.translate(
                input_file=intermediate_file,
                source_format=intermediate_format,
                target_format=source_format,
                output_file=roundtrip_file
            )
            
            if not result2.get('success'):
                errors.append(f"Return translation failed: {result2.get('error', 'Unknown error')}")
                return RoundtripResult(
                    source_file=str(source_file),
                    source_format=source_format,
                    intermediate_format=intermediate_format,
                    translation1_success=True,
                    translation2_success=False,
                    total_models=result1.get('models_translated', 0),
                    models_matched=0,
                    total_params=0,
                    params_matched=0,
                    match_rate=0.0,
                    model_comparisons=[],
                    errors=errors
                )
        except Exception as e:
            errors.append(f"Return translation exception: {str(e)}")
            return RoundtripResult(
                source_file=str(source_file),
                source_format=source_format,
                intermediate_format=intermediate_format,
                translation1_success=True,
                translation2_success=False,
                total_models=result1.get('models_translated', 0),
                models_matched=0,
                total_params=0,
                params_matched=0,
                match_rate=0.0,
                model_comparisons=[],
                errors=errors
            )
        
        # Step 3: Extract and compare parameters
        if source_format == 'spectre':
            orig_params = extract_parameters_from_spectre(source_file)
            rt_params = extract_parameters_from_spectre(roundtrip_file)
        else:
            orig_params = extract_parameters_from_file(source_file)
            rt_params = extract_parameters_from_file(roundtrip_file)
        
        # Compare
        comparisons = compare_models(orig_params, rt_params)
        
        # Calculate totals
        total_models = len(comparisons)
        models_matched = sum(1 for c in comparisons 
                            if len(c.mismatched) == 0 and len(c.missing) == 0)
        total_params = sum(c.total_params for c in comparisons)
        params_matched = sum(c.matched_params for c in comparisons)
        
        match_rate = params_matched / max(total_params, 1)
        
        return RoundtripResult(
            source_file=str(source_file),
            source_format=source_format,
            intermediate_format=intermediate_format,
            translation1_success=True,
            translation2_success=True,
            total_models=total_models,
            models_matched=models_matched,
            total_params=total_params,
            params_matched=params_matched,
            match_rate=match_rate,
            model_comparisons=comparisons,
            errors=errors
        )


def print_result(result: RoundtripResult, verbose: bool = False):
    """Print verification result"""
    print("=" * 70)
    print("ROUND-TRIP VERIFICATION RESULT")
    print("=" * 70)
    print(f"Source File:    {result.source_file}")
    print(f"Format:         {result.source_format} → {result.intermediate_format} → {result.source_format}")
    print()
    
    # Translation status
    t1_status = "✅" if result.translation1_success else "❌"
    t2_status = "✅" if result.translation2_success else "❌"
    print(f"Translation 1:  {t1_status} ({result.source_format} → {result.intermediate_format})")
    print(f"Translation 2:  {t2_status} ({result.intermediate_format} → {result.source_format})")
    print()
    
    if not result.translation1_success or not result.translation2_success:
        print("❌ Translation failed - cannot compare parameters")
        for err in result.errors:
            print(f"   Error: {err}")
        return
    
    # Summary
    print("PARAMETER COMPARISON:")
    print("-" * 40)
    print(f"Total Models:     {result.total_models}")
    print(f"Models Matched:   {result.models_matched}")
    print(f"Total Parameters: {result.total_params}")
    print(f"Params Matched:   {result.params_matched}")
    print(f"Match Rate:       {result.match_rate:.1%}")
    print()
    
    if result.match_rate >= 0.99:
        print("✅ EXCELLENT: >99% parameter match")
    elif result.match_rate >= 0.95:
        print("⚠️  GOOD: >95% parameter match")
    elif result.match_rate >= 0.80:
        print("⚠️  FAIR: >80% parameter match - review mismatches")
    else:
        print("❌ POOR: <80% parameter match - translation issues detected")
    
    # Detailed mismatches (if verbose or significant issues)
    if verbose or result.match_rate < 0.95:
        print()
        print("MISMATCHED PARAMETERS:")
        print("-" * 40)
        
        for comp in result.model_comparisons:
            if comp.mismatched or comp.missing:
                print(f"\n  Model: {comp.model_name}")
                print(f"    Matched: {comp.matched_params}/{comp.total_params}")
                
                for mm in comp.mismatched[:5]:  # Limit to first 5
                    print(f"    ❌ {mm.param_name}: {mm.original_value:.6g} → {mm.roundtrip_value:.6g} (err: {mm.relative_error:.2%})")
                
                if comp.missing:
                    print(f"    Missing: {', '.join(comp.missing[:5])}")
                if comp.extra:
                    print(f"    Extra: {', '.join(comp.extra[:5])}")


def main():
    parser = argparse.ArgumentParser(description="Round-Trip Translation Verification")
    parser.add_argument('input', type=Path, nargs='?',
                        help="Source file to verify")
    parser.add_argument('--format', '-f', type=str,
                        choices=['spectre', 'hspice', 'ngspice'],
                        help="Source format (auto-detected if not specified)")
    parser.add_argument('--all', action='store_true',
                        help="Run on all PDK source files")
    parser.add_argument('--verbose', '-v', action='store_true',
                        help="Verbose output")
    parser.add_argument('--output', '-o', type=Path,
                        help="Output JSON report file")
    
    args = parser.parse_args()
    
    if args.all:
        # Find all source files
        source_files = []
        pdk_dir = BASE_DIR / 'tools' / 'spice-libraries' / 'private-models'
        
        for pattern in ['**/*.scs', '**/*.sp', '**/*.l']:
            source_files.extend(pdk_dir.glob(pattern))
        
        print(f"Found {len(source_files)} source files")
        
        results = []
        for sf in source_files[:10]:  # Limit to first 10
            print(f"\nVerifying: {sf.name}")
            result = run_roundtrip_verification(sf, args.format)
            results.append(result)
            
            status = "✅" if result.match_rate >= 0.95 else "❌"
            print(f"  {status} Match rate: {result.match_rate:.1%}")
        
        # Summary
        avg_match = sum(r.match_rate for r in results) / len(results)
        print(f"\nOverall average match rate: {avg_match:.1%}")
        
    else:
        if not args.input:
            # Default to a known working file
            args.input = BASE_DIR / 'tools' / 'spice-libraries' / 'private-models' / 'cadence90' / 'spectre' / 'gpdk090_mos.scs'
            if not args.input.exists():
                print("Please specify an input file")
                return 1
        
        result = run_roundtrip_verification(args.input, args.format)
        print_result(result, verbose=args.verbose)
        
        if args.output:
            # Save JSON report
            with open(args.output, 'w') as f:
                # Convert dataclasses to dicts
                def to_dict(obj):
                    if hasattr(obj, '__dict__'):
                        return {k: to_dict(v) for k, v in obj.__dict__.items()}
                    elif isinstance(obj, list):
                        return [to_dict(v) for v in obj]
                    else:
                        return obj
                
                json.dump(to_dict(result), f, indent=2)
            print(f"\nReport saved to: {args.output}")
        
        return 0 if result.match_rate >= 0.95 else 1


if __name__ == '__main__':
    sys.exit(main())
