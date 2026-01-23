"""ngspice format parser for ngspice models.

This module provides parsing functionality for ngspice (.lib) files,
which use a syntax similar to SPICE with ngspice-specific extensions.
"""

import re
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import logging

from .base_parser import BaseParser

logger = logging.getLogger(__name__)


class NgspiceParser(BaseParser):
    """Parser for ngspice (.lib) format files."""

    def get_format_name(self) -> str:
        """Get the format name."""
        return 'ngspice'

    def parse(self, follow_includes: bool = False) -> List[Dict[str, Any]]:
        """Parse the ngspice file and extract model information.

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

        # Check if this is a library file with sections
        if self._is_library_file(content):
            return self._parse_library_file(content)

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

    def _is_library_file(self, content: str) -> bool:
        """Check if the content represents a library file with sections."""
        content_lower = content.lower()
        return '.lib ' in content_lower and '.endl' in content_lower

    def _parse_library_file(self, content: str) -> List[Dict[str, Any]]:
        """Parse a library file with .lib sections."""
        models = []

        # Split content into sections
        sections = self._extract_library_sections(content)

        for section_name, section_content in sections.items():
            logger.debug(f"Processing library section: {section_name}")

            # Parse each section as if it were a standalone file
            section_lines = section_content.split('\n')
            model_blocks = self._extract_model_blocks(section_lines)

            for block_lines, start_line in model_blocks:
                try:
                    model_info = self._parse_model_block(block_lines, start_line)
                    if model_info:
                        # Add section information to the model
                        model_info['section'] = section_name
                        models.append(model_info)
                except Exception as e:
                    logger.error(f"Failed to parse model block in section {section_name} at line {start_line}: {e}")

        logger.info(f"Parsed {len(models)} models from library file {self.file_path}")
        return models

    def _extract_library_sections(self, content: str) -> Dict[str, str]:
        """Extract .lib sections from library file content."""
        sections = {}
        lines = content.split('\n')

        current_section = None
        current_content = []
        section_stack = []

        for line in lines:
            line_lower = line.lower().strip()

            if line_lower.startswith('.lib '):
                # Extract section name
                parts = line.split()
                if len(parts) >= 2:
                    section_name = parts[1]
                    if current_section:
                        # Save previous section
                        sections[current_section] = '\n'.join(current_content)
                        current_content = []

                    current_section = section_name
                    section_stack.append(section_name)
                    current_content = []

            elif line_lower.startswith('.endl') and section_stack:
                # End current section
                if current_section:
                    sections[current_section] = '\n'.join(current_content)
                    current_content = []
                section_stack.pop()
                current_section = section_stack[-1] if section_stack else None

            elif current_section:
                current_content.append(line)

        # Handle any remaining content
        if current_section and current_content:
            sections[current_section] = '\n'.join(current_content)

        return sections

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
            if not line or line.startswith('*') or line.startswith('//') or line.startswith('$'):
                continue

            # Check for model start - ngspice uses .model syntax like HSPICE
            if not in_block and line.lower().startswith('.model '):
                in_block = True
                block_start = i + 1  # 1-indexed
                current_block = [line]
                continue

            if in_block:
                current_block.append(line)

                # Check if block is complete (new model starts or end of reasonable content)
                # ngspice models typically end when another .model starts or we hit certain keywords
                if (line.lower().startswith('.model ') and len(current_block) > 1) or \
                   line.lower().startswith('.end') or \
                   (i == len(lines) - 1 and current_block):  # End of file
                    # If we hit end of file, include the current block
                    if line.lower().startswith('.model ') and len(current_block) > 1:
                        # Remove the new model line from current block
                        current_block = current_block[:-1]
                    blocks.append((current_block, block_start))
                    current_block = []
                    in_block = False

                    # If we hit a new model, start it for next iteration
                    if line.lower().startswith('.model '):
                        in_block = True
                        block_start = i + 1
                        current_block = [line]

        # Don't forget the last block if file ends
        if current_block:
            blocks.append((current_block, block_start))

        return blocks

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

            # Skip empty lines, comments, and .end statements
            if not line or line.startswith('*') or line.startswith('//') or line.lower().startswith('.end'):
                continue

            # ngspice allows continuation with +
            if line.startswith('+'):
                line = line[1:].strip()

            # Parse parameter assignments
            line_params = self._parse_parameter_line(line)
            parameters.update(line_params)

        model_info['parameters'] = parameters
        model_info['line_number'] = start_line
        model_info['format'] = 'ngspice'

        return model_info

    def _parse_model_header(self, header_line: str) -> Optional[Dict[str, Any]]:
        """Parse the model header line.

        Args:
            header_line: The first line of the model block

        Returns:
            Basic model information dictionary
        """
        # Pattern: .model <name> <type> [level=<level>]
        # ngspice: .model NMOS_VTG nmos level = 54
        pattern = r'\.model\s+(\w+)\s+(\w+)(?:\s+level\s*=\s*(\d+))?'
        match = re.match(pattern, header_line, re.IGNORECASE)

        if not match:
            return None

        model_name = match.group(1)
        model_type = match.group(2)
        level = match.group(3) if match.group(3) else None

        # Determine model category
        category = self._classify_model_type(model_type)

        result = {
            'name': model_name,
            'type': model_type,
            'category': category,
            'pdk_name': self._extract_pdk_name(self.file_path),
            'corner': self._extract_corner(self.file_path)
        }

        if level:
            result['level'] = int(level)

        return result

    def _parse_parameter_line(self, line: str) -> Dict[str, Any]:
        """Parse a line containing parameter assignments.

        Args:
            line: Parameter line to parse

        Returns:
            Dictionary of parameter names to values
        """
        parameters = {}

        # ngspice parameters can be in various formats:
        # param=value param2=value2
        # param = value
        # Multiple parameters per line separated by spaces

        # Split by spaces but be careful about quoted values
        # This is a simplified version - real ngspice parsing needs more sophistication

        # Handle multiple parameters per line
        param_pattern = r'(\w+)\s*=\s*([^=\s]+(?:\s+[^=\s]+)*?)(?=\s+\w+\s*=|$)'
        matches = re.findall(param_pattern, line, re.IGNORECASE)

        for param_name, param_value in matches:
            param_name = param_name.strip().lower()
            param_value = param_value.strip()

            # Clean up the value - remove trailing commas, semicolons, etc.
            param_value = re.sub(r'[;,]\s*$', '', param_value)

            # Try to convert to numeric
            try:
                # Handle scientific notation, units, etc.
                if 'e' in param_value.lower() or '.' in param_value or param_value.replace('-', '').replace('+', '').isdigit():
                    # Check for units (e.g., 1e-6, 1.5n, 2.3p)
                    unit_match = re.match(r'^([+-]?\d*\.?\d+)[eE]?([+-]?\d+)?([a-zA-Z]*)$', param_value)
                    if unit_match:
                        number_part = unit_match.group(1)
                        exponent_part = unit_match.group(2) or '0'
                        unit_part = unit_match.group(3) or ''

                        # Convert scientific notation
                        if exponent_part:
                            value = float(number_part) * (10 ** int(exponent_part))
                        else:
                            value = float(number_part)

                        # Store with unit information
                        parameters[param_name] = {
                            'value': value,
                            'unit': unit_part,
                            'raw': param_value
                        }
                    else:
                        parameters[param_name] = float(param_value)
                else:
                    parameters[param_name] = param_value
            except (ValueError, AttributeError):
                # Keep as string if conversion fails
                parameters[param_name] = param_value

        return parameters

    def _classify_model_type(self, model_type: str) -> str:
        """Classify the model type into categories.

        Args:
            model_type: The model type from the header

        Returns:
            Model category (mos, bjt, diode, passive)
        """
        model_type_lower = model_type.lower()

        if model_type_lower in ['nmos', 'pmos', 'mos', 'nfet', 'pfet']:
            return 'mos'
        elif model_type_lower in ['npn', 'pnp', 'bjt', 'vbic', 'hicum', 'gummel_poon']:
            return 'bjt'
        elif model_type_lower in ['diode', 'd']:
            return 'diode'
        elif model_type_lower in ['resistor', 'capacitor', 'inductor', 'r', 'c', 'l']:
            return 'passive'
        else:
            return 'unknown'

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
