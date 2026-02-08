#!/usr/bin/env python3
"""
SPICE Translator - Command-line interface.

Translates SPICE model files between different formats using IR-based architecture.

Usage:
    python -m src.main translate input.scs output.lib --from spectre --to ngspice
    python -m src.main validate output.lib --format ngspice
    python -m src.main info input.scs --format spectre

Compliance: CONSTRAINTS.md
"""

import sys
import argparse
import logging
from pathlib import Path
from typing import Optional, List
import time

from src.parsers import SpectreParser, HSPICEParser, NgspiceParser
from src.writers import SpectreWriter, HSPICEWriter, NgspiceWriter
from src.validation import TranslationValidator, IRValidator, SyntaxValidator, SPICEFormat
from src.ir.model_ir import ModelIR
from src.utils import OutputManager

logger = logging.getLogger(__name__)


class TranslationEngine:
    """
    Main translation engine orchestrating the complete workflow.
    
    Workflow: Parse → Validate IR → Write → Validate Output
    """
    
    def __init__(self, verbose: bool = False, output_manager: OutputManager = None):
        """
        Initialize translation engine.
        
        Args:
            verbose: Enable verbose logging
            output_manager: OutputManager instance for organized output
        """
        self.verbose = verbose
        self.output_manager = output_manager or OutputManager()
        self._setup_logging()
    
    def _setup_logging(self) -> None:
        """Configure logging."""
        level = logging.DEBUG if self.verbose else logging.INFO
        logging.basicConfig(
            level=level,
            format='%(levelname)s: %(message)s'
        )
    
    def translate(
        self,
        input_file: Path,
        source_format: str,
        target_format: str,
        output_file: Path = None,
        validate: bool = True,
        strict: bool = False,
        use_organized_output: bool = True,
        follow_includes: bool = False
    ) -> dict:
        """
        Translate SPICE file from source to target format.
        
        Args:
            input_file: Input file path
            output_file: Output file path (optional, auto-generated if not provided)
            source_format: Source format (spectre, hspice, ngspice)
            target_format: Target format (spectre, hspice, ngspice)
            validate: Run validation after translation
            strict: Strict validation mode (warnings as errors)
            use_organized_output: Use organized output structure
            follow_includes: Resolve .include/.lib directives and merge content
            
        Returns:
            Translation result dictionary
        """
        start_time = time.time()
        
        # Auto-generate output path if not provided
        if output_file is None and use_organized_output:
            output_file = self.output_manager.get_output_path(
                input_file,
                source_format,
                target_format
            )
            logger.info(f"Auto-generated output path: {output_file}")
        elif output_file is None:
            # Fallback: same dir as input
            extensions = {'spectre': 'scs', 'hspice': 'sp', 'ngspice': 'lib'}
            ext = extensions[target_format.lower()]
            output_file = input_file.parent / f"{input_file.stem}_translated.{ext}"
        
        # Step 1: Parse source file to IR
        if follow_includes:
            logger.info(f"Parsing {source_format} file with include resolution: {input_file}")
        else:
            logger.info(f"Parsing {source_format} file: {input_file}")
        parser_class = self._get_parser(source_format)
        parser = parser_class(input_file)
        
        try:
            models = parser.parse_to_ir(follow_includes=follow_includes)
            if follow_includes and parser.included_files:
                logger.info(f"  Resolved {len(parser.included_files)} include(s)")
        except Exception as e:
            logger.error(f"Failed to parse input file: {e}")
            return {
                'success': False,
                'error': str(e),
                'stage': 'parsing'
            }
        
        logger.info(f"✓ Parsed {len(models)} models")
        
        # Step 2: Validate IR (optional)
        if validate:
            logger.info("Validating IR structure...")
            ir_validator = IRValidator(strict=strict)
            ir_result = ir_validator.validate(models)
            
            if not ir_result.valid:
                logger.error(f"IR validation failed: {ir_result.error_count} errors")
                for err in ir_result.errors[:5]:
                    logger.error(f"  - {err}")
                return {
                    'success': False,
                    'error': 'IR validation failed',
                    'stage': 'ir_validation',
                    'validation_result': ir_result
                }
            logger.info(f"✓ IR validation passed ({ir_result.warning_count} warnings)")
        
        # Step 3: Write to target format
        logger.info(f"Writing {target_format} file: {output_file}")
        writer_class = self._get_writer(target_format)
        writer = writer_class(output_file)
        
        try:
            writer.write_from_ir(models)
        except Exception as e:
            logger.error(f"Failed to write output file: {e}")
            return {
                'success': False,
                'error': str(e),
                'stage': 'writing'
            }
        
        logger.info(f"✓ Wrote {len(models)} models to {output_file}")
        
        # Step 4: Validate output (optional)
        if validate:
            logger.info("Validating output syntax...")
            try:
                syntax_format = SPICEFormat(target_format.lower())
                syntax_validator = SyntaxValidator(format=syntax_format, strict=strict)
                
                # Read output file
                output_content = output_file.read_text()
                syntax_result = syntax_validator.validate(output_content)
                
                if not syntax_result.valid:
                    logger.warning(f"Syntax validation failed: {syntax_result.error_count} errors")
                    for err in syntax_result.errors[:5]:
                        logger.warning(f"  - {err}")
                else:
                    logger.info(f"✓ Syntax validation passed ({syntax_result.warning_count} warnings)")
            except Exception as e:
                logger.warning(f"Could not validate syntax: {e}")
        
        elapsed = time.time() - start_time
        
        result = {
            'success': True,
            'models_translated': len(models),
            'input_file': str(input_file),
            'output_file': str(output_file),
            'source_format': source_format,
            'target_format': target_format,
            'elapsed_time': elapsed
        }
        
        logger.info(f"✓ Translation complete in {elapsed:.2f}s")
        return result
    
    def validate_file(
        self,
        file_path: Path,
        format_name: str,
        strict: bool = False
    ) -> dict:
        """
        Validate SPICE file syntax and structure.
        
        Args:
            file_path: File to validate
            format_name: SPICE format
            strict: Strict validation mode
            
        Returns:
            Validation result dictionary
        """
        logger.info(f"Validating {format_name} file: {file_path}")
        
        # Parse to IR
        parser_class = self._get_parser(format_name)
        parser = parser_class(file_path)
        try:
            models = parser.parse_to_ir()
        except Exception as e:
            return {
                'success': False,
                'error': f"Parse error: {e}"
            }
        
        # Validate IR
        ir_validator = IRValidator(strict=strict)
        ir_result = ir_validator.validate(models)
        
        # Validate syntax
        try:
            syntax_format = SPICEFormat(format_name.lower())
            syntax_validator = SyntaxValidator(format=syntax_format, strict=strict)
            content = file_path.read_text()
            syntax_result = syntax_validator.validate(content)
        except Exception as e:
            syntax_result = None
            logger.warning(f"Syntax validation skipped: {e}")
        
        success = ir_result.valid and (syntax_result is None or syntax_result.valid)
        
        return {
            'success': success,
            'models': len(models),
            'ir_validation': ir_result,
            'syntax_validation': syntax_result
        }
    
    def get_info(self, file_path: Path, format_name: str) -> dict:
        """
        Get information about SPICE file.
        
        Args:
            file_path: File to analyze
            format_name: SPICE format
            
        Returns:
            File information dictionary
        """
        parser_class = self._get_parser(format_name)
        parser = parser_class(file_path)
        
        try:
            models = parser.parse_to_ir()
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
        
        # Gather statistics
        device_types = {}
        total_params = 0
        total_variations = 0
        
        for model in models:
            device_type = str(model.device_type.value)
            device_types[device_type] = device_types.get(device_type, 0) + 1
            total_params += len(model.base_parameters)
            total_variations += len(model.variations)
        
        return {
            'success': True,
            'file': str(file_path),
            'format': format_name,
            'models': len(models),
            'device_types': device_types,
            'total_parameters': total_params,
            'total_variations': total_variations,
            'model_names': [m.name for m in models]
        }
    
    def _get_parser(self, format_name: str):
        """Get parser class for format."""
        parsers = {
            'spectre': SpectreParser,
            'hspice': HSPICEParser,
            'ngspice': NgspiceParser
        }
        
        parser_class = parsers.get(format_name.lower())
        if not parser_class:
            raise ValueError(f"Unknown format: {format_name}. Supported: {list(parsers.keys())}")
        
        return parser_class
    
    def _get_writer(self, format_name: str):
        """Get writer class for format."""
        writers = {
            'spectre': SpectreWriter,
            'hspice': HSPICEWriter,
            'ngspice': NgspiceWriter
        }
        
        writer_class = writers.get(format_name.lower())
        if not writer_class:
            raise ValueError(f"Unknown format: {format_name}. Supported: {list(writers.keys())}")
        
        return writer_class


def cmd_translate(args: argparse.Namespace) -> int:
    """Handle translate command."""
    engine = TranslationEngine(verbose=args.verbose)
    
    input_file = Path(args.input)
    
    if not input_file.exists():
        print(f"Error: Input file not found: {input_file}")
        return 1
    
    # Output file is now optional
    if args.output:
        output_file = Path(args.output)
        use_organized = False
    else:
        output_file = None
        use_organized = not args.no_organize
    
    result = engine.translate(
        input_file=input_file,
        output_file=output_file,
        source_format=args.from_format,
        target_format=args.to_format,
        validate=not args.no_validate,
        strict=args.strict,
        use_organized_output=use_organized
    )
    
    if result['success']:
        print(f"\n✓ Translation successful!")
        print(f"  Models: {result['models_translated']}")
        print(f"  Time: {result['elapsed_time']:.2f}s")
        print(f"  Output: {result['output_file']}")
        return 0
    else:
        print(f"\n✗ Translation failed at {result.get('stage', 'unknown')} stage")
        print(f"  Error: {result.get('error', 'Unknown error')}")
        return 1


def cmd_validate(args: argparse.Namespace) -> int:
    """Handle validate command."""
    engine = TranslationEngine(verbose=args.verbose)
    
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"Error: File not found: {file_path}")
        return 1
    
    result = engine.validate_file(
        file_path=file_path,
        format_name=args.format,
        strict=args.strict
    )
    
    if result['success']:
        print(f"\n✓ Validation passed!")
        print(f"  Models: {result['models']}")
        if result.get('ir_validation'):
            ir = result['ir_validation']
            print(f"  IR: {ir.error_count} errors, {ir.warning_count} warnings")
        return 0
    else:
        print(f"\n✗ Validation failed!")
        print(f"  Error: {result.get('error', 'Unknown error')}")
        return 1


def cmd_info(args: argparse.Namespace) -> int:
    """Handle info command."""
    engine = TranslationEngine(verbose=args.verbose)
    
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"Error: File not found: {file_path}")
        return 1
    
    result = engine.get_info(
        file_path=file_path,
        format_name=args.format
    )
    
    if result['success']:
        print(f"\n📄 File Information")
        print(f"  File: {result['file']}")
        print(f"  Format: {result['format']}")
        print(f"  Models: {result['models']}")
        print(f"  Parameters: {result['total_parameters']}")
        print(f"  Variations: {result['total_variations']}")
        print(f"\n  Device Types:")
        for dtype, count in result['device_types'].items():
            print(f"    - {dtype}: {count}")
        print(f"\n  Model Names:")
        for name in result['model_names'][:10]:
            print(f"    - {name}")
        if len(result['model_names']) > 10:
            print(f"    ... and {len(result['model_names']) - 10} more")
        return 0
    else:
        print(f"\n✗ Failed to read file")
        print(f"  Error: {result.get('error', 'Unknown error')}")
        return 1


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='SPICE Model Translator - IR-based architecture',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Translate Spectre to ngspice
  %(prog)s translate models.scs models.lib --from spectre --to ngspice
  
  # Validate HSPICE file
  %(prog)s validate models.lib --format hspice
  
  # Get file information
  %(prog)s info models.scs --format spectre
        '''
    )
    
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Translate command
    translate_parser = subparsers.add_parser('translate', help='Translate between formats')
    translate_parser.add_argument('input', help='Input file path')
    translate_parser.add_argument('output', nargs='?', default=None,
                                 help='Output file path (auto-generated if omitted)')
    translate_parser.add_argument('--from', dest='from_format', required=True,
                                 choices=['spectre', 'hspice', 'ngspice'],
                                 help='Source format')
    translate_parser.add_argument('--to', dest='to_format', required=True,
                                 choices=['spectre', 'hspice', 'ngspice'],
                                 help='Target format')
    translate_parser.add_argument('--no-validate', action='store_true',
                                 help='Skip validation')
    translate_parser.add_argument('--strict', action='store_true',
                                 help='Strict validation (warnings as errors)')
    translate_parser.add_argument('--no-organize', action='store_true',
                                 help='Disable organized output structure')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate SPICE file')
    validate_parser.add_argument('file', help='File to validate')
    validate_parser.add_argument('--format', required=True,
                                choices=['spectre', 'hspice', 'ngspice'],
                                help='SPICE format')
    validate_parser.add_argument('--strict', action='store_true',
                                help='Strict validation mode')
    
    # Info command
    info_parser = subparsers.add_parser('info', help='Display file information')
    info_parser.add_argument('file', help='File to analyze')
    info_parser.add_argument('--format', required=True,
                            choices=['spectre', 'hspice', 'ngspice'],
                            help='SPICE format')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    if args.command == 'translate':
        return cmd_translate(args)
    elif args.command == 'validate':
        return cmd_validate(args)
    elif args.command == 'info':
        return cmd_info(args)
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())
