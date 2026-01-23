"""Spectre format parser for Cadence SPICE models.

This module provides parsing functionality for Cadence Spectre (.scs) files,
which use a different syntax from HSPICE and ngspice formats.
"""

import re
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import logging

from .base_parser import BaseParser

logger = logging.getLogger(__name__)


class SpectreParser(BaseParser):
    """Parser for Cadence Spectre (.scs) format files."""

    def get_format_name(self) -> str:
        """Get the format name."""
        return 'spectre'

    def parse(self, follow_includes: bool = False) -> List[Dict[str, Any]]:
        """Parse the Spectre file and extract model information.

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

    def _load_file_with_includes(self, max_depth: int = 5, processed_files: set = None) -> str:
        """Load Spectre file content with include resolution, handling section-specific includes.

        Args:
            max_depth: Maximum include depth to prevent infinite recursion
            processed_files: Set of already processed files

        Returns:
            Combined content from main file and includes
        """
        if processed_files is None:
            processed_files = set()

        # Use file path as key for circular detection
        file_key = str(self.file_path)
        if file_key in processed_files:
            logger.warning(f"Circular include detected: {self.file_path}")
            return ""

        if max_depth <= 0:
            logger.warning(f"Maximum include depth exceeded for {self.file_path}")
            return ""

        processed_files.add(file_key)

        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                with open(self.file_path, 'r', encoding='latin-1') as f:
                    content = f.read()
            except Exception as e:
                logger.error(f"Failed to read file {self.file_path}: {e}")
                return ""
        except Exception as e:
            logger.error(f"Failed to read file {self.file_path}: {e}")
            return ""

        # Process includes
        lines = content.split('\n')
        processed_content = []

        for line in lines:
            processed_content.append(line)

            # Check for Spectre include statements
            stripped = line.strip().lower()
            if stripped.startswith('include '):
                include_info = self._extract_spectre_include_info(line)
                if include_info:
                    file_path, section_name = include_info
                    resolved_path = self._resolve_include_path(file_path)
                    if resolved_path and resolved_path.exists():
                        logger.info(f"Following Spectre include: {resolved_path} (section: {section_name})")
                        included_content = self._load_spectre_include_file(
                            resolved_path, section_name, max_depth - 1, processed_files.copy()
                        )
                        if included_content:
                            # Add included content as comments to preserve line numbers
                            processed_content.append(f"* BEGIN INCLUDE: {resolved_path} section={section_name}")
                            processed_content.extend(included_content.split('\n'))
                            processed_content.append(f"* END INCLUDE: {resolved_path}")
                    else:
                        logger.warning(f"Could not resolve Spectre include path: {file_path}")

        return '\n'.join(processed_content)

    def _extract_spectre_include_info(self, line: str) -> Optional[Tuple[str, str]]:
        """Extract file path and section name from Spectre include statement.

        Args:
            line: Include statement line (e.g., 'include "file.scs" section=tt')

        Returns:
            Tuple of (file_path, section_name) or None
        """
        import re

        # Pattern to match: include "file.scs" section=tt
        pattern = r'include\s+["\']([^"\']+)["\']\s+section\s*=\s*(\w+)'
        match = re.search(pattern, line, re.IGNORECASE)
        if match:
            file_path = match.group(1)
            section_name = match.group(2)
            return file_path, section_name

        # Fallback: just extract file path if no section specified
        file_path = self._extract_include_path(line)
        if file_path:
            return file_path, 'all'  # 'all' means include entire file

        return None

    def _load_spectre_include_file(self, file_path: Path, section_name: str,
                                  max_depth: int, processed_files: set) -> str:
        """Load a Spectre include file, optionally extracting only a specific section.

        Args:
            file_path: Path to the include file
            section_name: Section name to extract ('all' for entire file)
            max_depth: Maximum include depth
            processed_files: Set of already processed files

        Returns:
            Content from the file/section
        """
        # Use file + section combination as key for circular detection
        file_key = f"{str(file_path)}:{section_name}" if section_name != 'all' else str(file_path)

        if file_key in processed_files:
            logger.warning(f"Circular include detected: {file_path} section={section_name}")
            return ""

        if max_depth <= 0:
            logger.warning(f"Maximum include depth exceeded for {file_path}")
            return ""

        processed_files.add(file_key)

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    content = f.read()
            except Exception as e:
                logger.error(f"Failed to read include file {file_path}: {e}")
                return ""
        except Exception as e:
            logger.error(f"Failed to read include file {file_path}: {e}")
            return ""

        if section_name == 'all':
            # Recursively process includes in the entire file
            return self._process_includes_in_content(content, file_path, max_depth, processed_files)

        # Extract specific section
        lines = content.split('\n')
        section_content = []
        in_section = False
        section_depth = 0

        for line in lines:
            stripped = line.strip().lower()

            if not in_section:
                if stripped == f'section {section_name}':
                    in_section = True
                    section_depth = 1
                    section_content.append(f"* EXTRACTED SECTION: {section_name}")
                    continue
            else:
                if stripped == f'section {section_name}':
                    section_depth += 1
                elif stripped == 'endsection' or stripped == f'endsection {section_name}':
                    section_depth -= 1
                    if section_depth == 0:
                        in_section = False
                        section_content.append(f"* END SECTION: {section_name}")
                        break
                else:
                    section_content.append(line)

        if section_content:
            extracted_content = '\n'.join(section_content)
            # Recursively process includes in the extracted section
            return self._process_includes_in_content(extracted_content, file_path, max_depth, processed_files)
        else:
            logger.warning(f"Section '{section_name}' not found in {file_path}")
            return ""

    def _process_includes_in_content(self, content: str, base_path: Path,
                                    max_depth: int, processed_files: set) -> str:
        """Process includes within a block of content.

        Args:
            content: Content to process
            base_path: Base path for resolving relative includes
            max_depth: Maximum include depth
            processed_files: Set of already processed files

        Returns:
            Content with includes resolved
        """
        lines = content.split('\n')
        processed_content = []

        for line in lines:
            processed_content.append(line)

            # Check for Spectre include statements
            stripped = line.strip().lower()
            if stripped.startswith('include '):
                include_info = self._extract_spectre_include_info(line)
                if include_info:
                    file_path, section_name = include_info
                    # Resolve relative to the base file
                    resolved_path = self._resolve_include_path_from_base(file_path, base_path)
                    if resolved_path and resolved_path.exists():
                        logger.info(f"Following nested Spectre include: {resolved_path} (section: {section_name})")
                        included_content = self._load_spectre_include_file(
                            resolved_path, section_name, max_depth - 1, processed_files.copy()
                        )
                        if included_content:
                            processed_content.append(f"* BEGIN NESTED INCLUDE: {resolved_path} section={section_name}")
                            processed_content.extend(included_content.split('\n'))
                            processed_content.append(f"* END NESTED INCLUDE: {resolved_path}")
                    else:
                        logger.warning(f"Could not resolve nested Spectre include path: {file_path}")

        return '\n'.join(processed_content)

    def _resolve_include_path_from_base(self, include_path: str, base_path: Path) -> Optional[Path]:
        """Resolve include path relative to a specific base file.

        Args:
            include_path: Include path from statement
            base_path: Base file path for resolution

        Returns:
            Resolved absolute path or None
        """
        # Try relative to base file directory
        relative_path = base_path.parent / include_path
        if relative_path.exists():
            return relative_path

        # Fall back to the standard resolution
        return self._resolve_include_path(include_path)

    def _extract_model_blocks(self, lines: List[str]) -> List[Tuple[List[str], int]]:
        """Extract model and subcircuit blocks from the file lines.

        Args:
            lines: All lines from the file

        Returns:
            List of (block_lines, start_line_number) tuples
        """
        blocks = []
        current_block = []
        in_block = False
        block_start = 0
        block_type = None  # 'model' or 'subckt'

        for i, line in enumerate(lines):
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith('//') or line.startswith('*'):
                continue

            # Check for block start
            if not in_block:
                if line.startswith('model '):
                    in_block = True
                    block_start = i + 1  # 1-indexed
                    current_block = [line]
                    block_type = 'model'
                    continue
                elif line.startswith('inline subckt '):
                    in_block = True
                    block_start = i + 1  # 1-indexed
                    current_block = [line]
                    block_type = 'subckt'
                    continue

            if in_block:
                current_block.append(line)

                # Check if block is complete (next model, subckt, section, or ends)
                if (line.startswith('model ') or
                    line.startswith('inline subckt') or
                    line.startswith('section ') or
                    line.startswith('endsection ') or
                    line.startswith('ends ') or
                    line.startswith('library ')):
                    # End the current block before the new one starts
                    if current_block:
                        blocks.append((current_block, block_start))
                        current_block = []
                        in_block = False

                    # If it's a new block, start a new one
                    if line.startswith('model ') or line.startswith('inline subckt'):
                        in_block = True
                        block_start = i + 1
                        current_block = [line]
                        block_type = 'model' if line.startswith('model ') else 'subckt'
                else:
                    current_block.append(line)

        # Handle unclosed block at end of file
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

            # Skip empty lines, comments, and closing braces
            if not line or line.startswith('//') or line.startswith('*') or line == '}':
                continue

            # Remove continuation + if present
            if line.startswith('+'):
                line = line[1:].strip()

            # Parse parameter assignments
            line_params = self._parse_parameter_line(line)
            parameters.update(line_params)

        model_info['parameters'] = parameters
        model_info['line_number'] = start_line
        model_info['format'] = 'spectre'

        return model_info

    def _parse_model_header(self, header_line: str) -> Optional[Dict[str, Any]]:
        """Parse the model or subcircuit header line.

        Args:
            header_line: The first line of the model/subcircuit block

        Returns:
            Basic model/subcircuit information dictionary
        """
        header_line = header_line.strip()

        # Check if it's a model or subcircuit
        if header_line.startswith('model '):
            # Pattern: model <name> <type> (with optional { )
            pattern = r'model\s+(\w+)\s+(\w+)(\s*\{)?'
            match = re.match(pattern, header_line, re.IGNORECASE)

            if not match:
                return None

            model_name = match.group(1)
            model_type = match.group(2)

            # Determine model category
            category = self._classify_model_type(model_type)

            return {
                'name': model_name,
                'type': model_type,
                'category': category,
                'block_type': 'model',
                'pdk_name': self._extract_pdk_name(self.file_path),
                'corner': self._extract_corner(self.file_path)
            }

        elif header_line.startswith('inline subckt '):
            # Pattern: inline subckt <name> ( <ports> )
            pattern = r'inline\s+subckt\s+(\w+)\s*\(\s*([^)]*)\s*\)'
            match = re.match(pattern, header_line, re.IGNORECASE)

            if not match:
                return None

            subckt_name = match.group(1)
            ports_str = match.group(2)

            # Parse ports
            ports = [p.strip() for p in ports_str.split(',') if p.strip()]

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
            line: Parameter line to parse

        Returns:
            Dictionary of parameter names to values
        """
        parameters = {}

        # Handle multiple parameters per line, separated by spaces
        # Parameters can be: param=value param2=value2 etc.
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

        if model_type_lower in ['bsim4', 'bsim3', 'mos', 'nch', 'pch', 'pmos', 'nmos']:
            return 'mos'
        elif model_type_lower in ['bjt', 'vbic', 'hicum', 'gummel_poon']:
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
            if 'pdk' in part.lower() or part in ['freepdk45', 'sky130', 'ihp', 'tsmc', 'smic', 'cadence']:
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
