"""Generic SPICE format parser for various SPICE dialects.

This module provides parsing functionality for generic SPICE files that don't
fit traditional HSPICE, ngspice, or Spectre formats, such as Sky130 and other
PDK-specific formats.
"""

import re
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import logging

from .base_parser import BaseParser

logger = logging.getLogger(__name__)


class GenericSPICEParser(BaseParser):
    """Parser for generic SPICE format files."""

    def get_format_name(self) -> str:
        """Get the format name."""
        return 'generic'
    
    def __init__(self, *args, **kwargs):
        """Initialize the GenericSPICEParser with enhanced expression parsing support."""
        super().__init__(*args, **kwargs)
        # Parameter context for expression parsing and parameter substitution
        self.parameter_context = {}

    def parse(self, follow_includes: bool = False) -> List[Dict[str, Any]]:
        """Parse the generic SPICE file and extract model information.

        Args:
            follow_includes: Whether to follow include statements

        Returns:
            List of model dictionaries containing parameters and metadata
        """
        # Use include-aware loading if requested
        if follow_includes:
            content = self._load_file_with_includes()
        else:
            content = self.content

        if not content:
            logger.warning(f"No content loaded for {self.file_path}")
            return []

        self.models = []
        lines = content.split('\n')

        # Check for different file types
        if self._is_include_only_file(content):
            # File only contains includes - parse recursively if requested
            if follow_includes:
                return self.models  # Includes already processed above
            else:
                logger.info(f"File {self.file_path} contains only includes, use follow_includes=True to parse included files")
                return []

        # Find all model blocks
        model_blocks = self._extract_model_blocks(lines)

        for block_lines, start_line in model_blocks:
            try:
                model_info = self._parse_model_block(block_lines, start_line)
                if model_info:
                    self.models.append(model_info)
            except Exception as e:
                logger.error(f"Failed to parse model block at line {start_line}: {e}")

        logger.info(f"Parsed {len(self.models)} models from {self.file_path}")
        return self.models

    def _classify_model_type(self, model_type: str) -> str:
        """Classify the model type into categories.

        Args:
            model_type: The model type from the header

        Returns:
            Model category (mos, bjt, diode, passive)
        """
        model_type_lower = model_type.lower()

        if model_type_lower in ['nmos', 'pmos', 'mos', 'nfet', 'pfet', 'bsim4', 'bsim3']:
            return 'mos'
        elif model_type_lower in ['npn', 'pnp', 'bjt', 'vbic', 'hicum', 'gummel_poon', 'mextram']:
            return 'bjt'
        elif model_type_lower in ['d', 'diode', 'dio']:
            return 'diode'
        elif model_type_lower in ['r', 'c', 'l', 'resistor', 'capacitor', 'inductor']:
            return 'passive'
        else:
            return 'unknown'

    def _is_include_only_file(self, content: str) -> bool:
        """Check if file contains only include statements."""
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        # Remove comments
        lines = [line for line in lines if not (line.startswith('*') or line.startswith('//'))]

        # Check if all remaining lines are includes
        return all(line.lower().startswith('.include') for line in lines)

    def _extract_model_blocks(self, lines: List[str]) -> List[Tuple[List[str], int]]:
        """Extract model blocks from the file lines.

        Args:
            lines: All lines from the file

        Returns:
            List of (block_lines, start_line_number) tuples
        """
        blocks = []
        current_block = []
        in_block = False
        block_start = 0

        for i, line in enumerate(lines):
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith('*') or line.startswith('//'):
                continue

            # Check for model start (various formats)
            if not in_block and self._is_model_start(line):
                in_block = True
                block_start = i + 1  # 1-indexed
                current_block = [line]
                continue

            if in_block:
                current_block.append(line)

                # Check if block is complete (new model or end markers)
                if (self._is_model_start(line) and len(current_block) > 1) or \
                   line.lower().startswith('.end') or \
                   line.lower().startswith('ends ') or \
                   (i == len(lines) - 1 and current_block):  # End of file
                    # If we hit end of file, include the current block
                    if self._is_model_start(line) and len(current_block) > 1:
                        # Remove the new model line from current block
                        current_block = current_block[:-1]
                    blocks.append((current_block, block_start))
                    current_block = []
                    in_block = False

        return blocks

    def _is_model_start(self, line: str) -> bool:
        """Check if line starts a model definition."""
        line_lower = line.lower()
        return (line_lower.startswith('.model ') or
                line_lower.startswith('model ') or
                line_lower.startswith('.subckt ') or
                line_lower.startswith('subckt '))

    def _parse_model_block(self, block_lines: List[str], start_line: int) -> Optional[Dict[str, Any]]:
        """Parse a single model block.

        Args:
            block_lines: Lines of the model block
            start_line: Starting line number (1-indexed)

        Returns:
            Model information dictionary or None if parsing failed
        """
        if not block_lines:
            return None

        # Parse the model header
        header_line = block_lines[0].strip()
        model_info = self._parse_model_header(header_line)

        if not model_info:
            return None

        # Parse parameters from the remaining lines
        parameters = {}
        for line in block_lines[1:]:
            line = line.strip()

            # Skip empty lines, comments, and closing markers
            if not line or line.startswith('*') or line.startswith('//') or \
               line.lower() in ['.end', '.ends', 'ends']:
                continue

            # Handle continuation lines (may use + or just continuation)
            if line.startswith('+'):
                line = line[1:].strip()

            # Parse parameter assignments
            line_params = self._parse_parameter_line(line)
            parameters.update(line_params)
            
            # Update parameter context for expression parsing
            # Extract simple numeric values for context
            for param_name, param_value in line_params.items():
                if isinstance(param_value, (int, float)):
                    self.parameter_context[param_name] = param_value
                elif isinstance(param_value, dict) and 'value' in param_value:
                    # Handle enriched parameter entries
                    if isinstance(param_value['value'], (int, float)):
                        self.parameter_context[param_name] = param_value['value']

        model_info['parameters'] = parameters
        model_info['line_number'] = start_line
        model_info['format'] = 'generic'

        return model_info

    def _parse_model_header(self, header_line: str) -> Optional[Dict[str, Any]]:
        """Parse the model header line.

        Args:
            header_line: The first line of the model block

        Returns:
            Basic model information dictionary
        """
        header_line = header_line.lower().strip()

        # Pattern: .model <name> <type>
        if header_line.startswith('.model '):
            pattern = r'\.model\s+(\w+)\s+(\w+)'
            match = re.match(pattern, header_line, re.IGNORECASE)

            if match:
                model_name = match.group(1)
                model_type = match.group(2)

                return {
                    'name': model_name,
                    'type': model_type,
                    'category': self._classify_model_type(model_type),
                    'block_type': 'model',
                    'pdk_name': self._extract_pdk_name(self.file_path),
                    'corner': self._extract_corner(self.file_path)
                }

        # Pattern: .subckt <name> <ports>
        elif header_line.startswith('.subckt '):
            pattern = r'\.subckt\s+(\w+)(.*)'
            match = re.match(pattern, header_line, re.IGNORECASE)

            if match:
                subckt_name = match.group(1)
                ports_str = match.group(2).strip()

                # Parse ports (space or tab separated)
                ports = [p for p in ports_str.split() if p]

                return {
                    'name': subckt_name,
                    'type': 'subckt',
                    'category': 'subcircuit',
                    'block_type': 'subckt',
                    'ports': ports,
                    'pdk_name': self._extract_pdk_name(self.file_path),
                    'corner': self._extract_corner(self.file_path)
                }

        # Pattern: model <name> <type> (Spectre style)
        elif header_line.startswith('model '):
            pattern = r'model\s+(\w+)\s+(\w+)'
            match = re.match(pattern, header_line, re.IGNORECASE)

            if match:
                model_name = match.group(1)
                model_type = match.group(2)

                return {
                    'name': model_name,
                    'type': model_type,
                    'category': self._classify_model_type(model_type),
                    'block_type': 'model',
                    'pdk_name': self._extract_pdk_name(self.file_path),
                    'corner': self._extract_corner(self.file_path)
                }

        # Pattern: subckt <name> <ports> (SPICE style)
        elif header_line.startswith('subckt '):
            pattern = r'subckt\s+(\w+)(.*)'
            match = re.match(pattern, header_line, re.IGNORECASE)

            if match:
                subckt_name = match.group(1)
                ports_str = match.group(2).strip()

                # Parse ports (space or tab separated)
                ports = [p for p in ports_str.split() if p]

                return {
                    'name': subckt_name,
                    'type': 'subckt',
                    'category': 'subcircuit',
                    'block_type': 'subckt',
                    'ports': ports,
                    'pdk_name': self._extract_pdk_name(self.file_path),
                    'corner': self._extract_corner(self.file_path)
                }

        return None

    def _parse_parameter_line(self, line: str) -> Dict[str, Any]:
        """Parse a line containing parameter assignments.

        Args:
            line: The line to parse

        Returns:
            Dictionary of parameter names to values
        """
        params = {}

        # Handle different parameter formats:
        # param = value
        # param=value
        # + param = value

        # Split by common separators
        parts = re.split(r'[=\s]+', line)

        i = 0
        while i < len(parts) - 1:
            param_name = parts[i].strip()
            param_value = parts[i + 1].strip()

            # Clean up parameter name
            param_name = re.sub(r'^[^\w]+', '', param_name)  # Remove leading non-word chars
            param_name = re.sub(r'[^\w]+$', '', param_name)  # Remove trailing non-word chars

            # Enhanced parameter value parsing using expression parser
            try:
                from .expression_parser import parse_parameter_value
                
                # Use enhanced expression parser for complex values
                parsed_result = parse_parameter_value(param_value, self.parameter_context)
                
                if parsed_result.success:
                    param_value = parsed_result.value
                    
                    # Store additional metadata if the parsed value is complex
                    if parsed_result.dependencies:
                        # Create enriched parameter entry with metadata
                        param_value = {
                            'value': parsed_result.value,
                            'original_expression': parsed_result.original,
                            'dependencies': parsed_result.dependencies,
                            'expression_type': parsed_result.expression_type.value,
                            'confidence': parsed_result.confidence
                        }
                else:
                    # Fallback to original basic parsing
                    try:
                        if '.' in param_value or 'e' in param_value.lower():
                            param_value = float(param_value)
                        else:
                            param_value = int(param_value)
                    except ValueError:
                        param_value = param_value.strip('"\'')
                        
            except ImportError:
                # Fallback to original parsing if expression parser not available
                try:
                    if '.' in param_value or 'e' in param_value.lower():
                        param_value = float(param_value)
                    else:
                        param_value = int(param_value)
                except ValueError:
                    param_value = param_value.strip('"\'')

            if param_name and param_name != '=':
                params[param_name] = param_value

            i += 2

        return params

    def _extract_pdk_name(self, file_path: Path) -> str:
        """Extract PDK name from file path.

        Args:
            file_path: Path to the model file

        Returns:
            PDK name
        """
        # Try to extract from path components
        parts = file_path.parts
        for part in reversed(parts):
            if 'pdk' in part.lower() or part in ['freepdk45', 'sky130', 'ihp', 'tsmc', 'smic', 'cadence', 'synopsys']:
                return part

        # Default fallback
        return 'unknown'

    def _extract_corner(self, file_path: Path) -> str:
        """Extract process corner from file path.

        Args:
            file_path: Path to the model file

        Returns:
            Process corner (tt, ff, ss, etc.)
        """
        # Look for corner indicators in filename or path
        path_str = str(file_path).lower()

        corners = ['tt', 'ff', 'ss', 'fs', 'sf', 'mc', 'typical', 'fast', 'slow']
        for corner in corners:
            if corner in path_str:
                return corner

        return 'tt'  # Default to typical
