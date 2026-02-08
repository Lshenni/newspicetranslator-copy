"""
HSPICE format parser with IR output.

Parses Synopsys HSPICE .sp/.lib files and converts to ModelIR representation.
Handles .lib sections, .model cards, and continuation lines.

Compliance: CONSTRAINTS.md
"""

from typing import List, Dict, Any, Optional, Set
from pathlib import Path
import re
import logging

from .base_parser import BaseParser
from .expression_parser import EnhancedExpressionParser
from .param_parsing import parse_param_string, strip_inline_comment
from ..ir.model_ir import (
    ModelIR,
    Condition,
    Corner,
    Temperature,
    DeviceType,
)

logger = logging.getLogger(__name__)


class HSPICEParser(BaseParser):
    """
    Parser for Synopsys HSPICE format (.sp, .lib files).

    HSPICE files use:
    - .lib <name> for library sections
    - .model <name> <type> <params> for model cards
    - + for continuation lines

    Converts HSPICE models to universal IR representation.
    """

    # Continuation line indicator
    CONTINUATION_CHAR = "+"

    def __init__(self, file_path: Path) -> None:
        """
        Initialize HSPICE parser.

        Args:
            file_path: Path to HSPICE .sp or .lib file
        """
        super().__init__(file_path)
        self.expr_parser = EnhancedExpressionParser()
        self.current_lib: Optional[str] = None
        self.included_files: Set[Path] = set()

    def get_format_name(self) -> str:
        """
        Get format identifier.

        Returns:
            Format name 'hspice'
        """
        return "hspice"

    def parse_to_ir(self, follow_includes: bool = False) -> List[ModelIR]:
        """
        Parse HSPICE file to IR representation.

        Args:
            follow_includes: Whether to recursively parse include files

        Returns:
            List of ModelIR objects extracted from file

        Raises:
            ValueError: If file content is empty or invalid
        """
        if not self.content:
            error_msg = f"No content loaded for {self.file_path}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Validate content
        if not self.validate_content():
            raise ValueError(f"Invalid content in {self.file_path}")

        # Load includes if requested
        if follow_includes:
            content = self._load_with_includes()
        else:
            content = self.content

        # Join continuation lines
        content = self._join_continuation_lines(content)

        # Extract model cards
        model_cards = self._extract_model_cards(content)

        # Convert each card to IR
        ir_models: List[ModelIR] = []
        for card in model_cards:
            try:
                ir_model = self._card_to_ir(card)
                if ir_model:
                    ir_models.append(ir_model)
            except Exception as e:
                logger.warning(
                    f"Error converting card '{card.get('name', 'unknown')}' "
                    f"to IR: {e}"
                )
                continue

        logger.info(
            f"Parsed {len(ir_models)} models from {self.file_path.name}"
        )
        return ir_models

    def _join_continuation_lines(self, content: str) -> str:
        """
        Join continuation lines (lines starting with +).

        Args:
            content: Raw file content

        Returns:
            Content with continuation lines joined
        """
        lines = content.split("\n")
        joined_lines: List[str] = []
        current_line = ""

        for line in lines:
            stripped = line.strip()

            # Ignore empty lines without breaking continuation context
            if not stripped:
                joined_lines.append(line)
                continue

            # Skip comment lines (HSPICE comment lines start with '*' or '$')
            if stripped.startswith("*") or stripped.startswith("$"):
                joined_lines.append(line)
                continue

            # Remove inline comments (safe: respects quotes; '*' only if preceded by whitespace)
            line = strip_inline_comment(line, markers=("$", "*"))
            stripped = line.strip()

            # Continuation line
            if stripped.startswith(self.CONTINUATION_CHAR):
                # Remove leading + and append to current line
                current_line += " " + stripped[1:].strip()
            else:
                # New line
                if current_line:
                    joined_lines.append(current_line)
                current_line = line

        # Add last line
        if current_line:
            joined_lines.append(current_line)

        return "\n".join(joined_lines)

    def _extract_model_cards(
        self, content: str
    ) -> List[Dict[str, Any]]:
        """
        Extract .model cards from HSPICE content.

        Args:
            content: HSPICE file content (continuation lines joined)

        Returns:
            List of model card dictionaries
        """
        cards: List[Dict[str, Any]] = []
        lines = content.split("\n")
        current_lib: Optional[str] = None

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Skip empty and comment lines
            if not stripped or stripped.startswith(
                ("*", "$", "**")
            ):
                continue

            # Library section
            if stripped.lower().startswith(".lib "):
                match = re.match(
                    r"\.lib\s+(\w+)", stripped, re.IGNORECASE
                )
                if match:
                    current_lib = match.group(1)
                    logger.debug(f"Entering library: {current_lib}")
                continue

            elif stripped.lower().startswith(".endl"):
                logger.debug(f"Exiting library: {current_lib}")
                current_lib = None
                continue

            # Model card: .model <name> <type> <params>
            if stripped.lower().startswith(".model "):
                card = self._parse_model_card(
                    stripped, i, current_lib
                )
                if card:
                    cards.append(card)

        logger.debug(f"Extracted {len(cards)} model cards")
        return cards

    def _parse_model_card(
        self,
        line: str,
        line_num: int,
        lib_section: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        """
        Parse a single .model card.

        Args:
            line: Model card line (continuation already joined)
            line_num: Line number in file
            lib_section: Current library section name

        Returns:
            Model card dictionary or None if invalid
        """
        # Remove .model prefix
        line = re.sub(r"^\.model\s+", "", line, flags=re.IGNORECASE)

        # Parse: <name> <type> <params>
        parts = line.split(None, 2)
        if len(parts) < 2:
            logger.debug(f"Invalid model card at line {line_num}: {line}")
            return None

        name = parts[0]
        model_type = parts[1]
        param_str = parts[2] if len(parts) > 2 else ""

        return {
            "name": name,
            "type": model_type,
            "param_str": param_str,
            "lib_section": lib_section,
            "line_num": line_num,
        }

    def _card_to_ir(
        self, card: Dict[str, Any]
    ) -> Optional[ModelIR]:
        """
        Convert parsed model card to ModelIR.

        Args:
            card: Card dictionary from _parse_model_card

        Returns:
            ModelIR object or None if conversion fails
        """
        name = card["name"]
        model_type = card["type"]
        param_str = card["param_str"]
        lib_section = card.get("lib_section")

        # Classify device type
        device_type = self._classify_device_type(name, model_type)

        # Parse parameters
        parameters = self._parse_parameter_string(param_str)

        # Create IR model
        ir_model = ModelIR(
            name=name,
            device_type=device_type,
            model_type=model_type,
        )
        ir_model.metadata["source_format"] = "hspice"

        # If in a library section, try to create variation
        if lib_section:
            try:
                # Try to parse library name as corner
                corner = Corner.from_string(lib_section.upper())
                condition = Condition(
                    corner=corner, temperature=Temperature.NOMINAL
                )

                ir_model.add_variation(
                    condition=condition,
                    parameters=parameters,
                    source_line=card["line_num"],
                    source_file=str(self.file_path),
                )

            except ValueError:
                # Not a standard corner, use as base parameters
                logger.debug(
                    f"Library '{lib_section}' not a standard corner, "
                    f"using as base parameters"
                )
                ir_model.base_parameters = parameters
        else:
            # No library section, use as base parameters
            ir_model.base_parameters = parameters

        return ir_model

    def _parse_parameter_string(
        self, param_str: str
    ) -> Dict[str, Any]:
        """
        Parse parameter string into key-value dictionary.

        Args:
            param_str: Parameter string from model card

        Returns:
            Parameter dictionary with evaluated values
        """
        parameters: Dict[str, Any] = {}

        raw_params = parse_param_string(param_str)

        for param_name, raw_value in raw_params.items():
            # Trim common trailing punctuation
            param_value_str = raw_value.strip().rstrip(",;")
            # If value is quoted, try parsing inner expression but preserve raw on failure
            parse_candidate = param_value_str
            if (
                len(parse_candidate) >= 2
                and parse_candidate[0] == parse_candidate[-1]
                and parse_candidate[0] in ("'", '"')
            ):
                parse_candidate = parse_candidate[1:-1].strip()

            # Evaluate expression
            try:
                result = self.expr_parser.parse_expression(parse_candidate)
                if result.success:
                    param_value = result.value
                else:
                    # Keep as string if parsing fails
                    param_value = param_value_str
                    logger.debug(
                        f"Could not parse '{param_name}={param_value_str}': "
                        f"{result.error_message}"
                    )
            except Exception as e:
                param_value = param_value_str
                logger.debug(
                    f"Exception parsing '{param_name}={param_value_str}': {e}"
                )

            parameters[param_name] = param_value

        return parameters

    def _classify_device_type(
        self, name: str, model_type: str
    ) -> DeviceType:
        """
        Classify device type from model name and type.

        Args:
            name: Model name (e.g., 'nmos_lvt', 'pmos_rvt')
            model_type: Model type string (e.g., 'nmos', 'pmos')

        Returns:
            DeviceType enum value
        """
        name_lower = name.lower()
        type_lower = model_type.lower()

        # Direct type matching - HSPICE uses single letter types
        if type_lower in ["nmos", "nch", "nfet", "n"]:
            return DeviceType.NMOS
        if type_lower in ["pmos", "pch", "pfet", "p"]:
            return DeviceType.PMOS
        if type_lower in ["npn"]:
            return DeviceType.NPN
        if type_lower in ["pnp"]:
            return DeviceType.PNP
        # Diode - HSPICE uses 'd' for diode model type
        if type_lower in ["d", "diode"]:
            return DeviceType.DIODE
        # Resistor - HSPICE uses 'r' for resistor model type
        if type_lower in ["r", "resistor", "res"]:
            return DeviceType.RESISTOR
        # Capacitor - HSPICE uses 'c' for capacitor model type
        if type_lower in ["c", "capacitor", "cap"]:
            return DeviceType.CAPACITOR

        # Name-based detection for MOSFET
        if any(
            x in name_lower
            for x in ["nmos", "nch", "nfet", "nwell"]
        ):
            return DeviceType.NMOS
        if any(
            x in name_lower
            for x in ["pmos", "pch", "pfet", "pwell"]
        ):
            return DeviceType.PMOS

        # BJT detection
        if any(x in type_lower for x in ["bjt", "vbic"]):
            return (
                DeviceType.NPN
                if "npn" in name_lower
                else DeviceType.PNP
            )

        # Name-based diode detection
        if any(x in name_lower for x in ["dio", "diode", "ndio", "pdio", "d_"]):
            return DeviceType.DIODE

        # Name-based resistor detection
        if any(x in name_lower for x in ["res", "rpo", "rdif", "rm", "rnw"]):
            return DeviceType.RESISTOR

        # Name-based capacitor detection
        if any(x in name_lower for x in ["cap", "mim", "mom", "var"]):
            return DeviceType.CAPACITOR

        logger.warning(
            f"Could not classify device type for name='{name}', "
            f"type='{model_type}', defaulting to NMOS"
        )
        return DeviceType.NMOS  # Default fallback

    def _load_with_includes(self) -> str:
        """
        Load file content with include directives resolved.

        Recursively loads files referenced by .include and .lib statements.
        
        Handles:
        - .include "filename" or .inc 'filename' - includes entire file
        - .lib "filename" section_name - includes specific section from library file

        Returns:
            Combined content with all includes resolved
        """
        if not self.content:
            return ""

        combined_content = []
        lines = self.content.split("\n")

        for line in lines:
            stripped = line.strip()
            
            # Check for .lib "file" section directive (HSPICE library include)
            # Format: .lib "path/to/file.lib" section_name
            lib_match = re.match(
                r'\s*\.lib\s+["\']([^"\']+)["\']\s+(\w+)',
                stripped,
                re.IGNORECASE,
            )
            if lib_match:
                lib_path = lib_match.group(1)
                section_name = lib_match.group(2)
                resolved_path = self._resolve_include_path(lib_path)
                
                if resolved_path and resolved_path not in self.included_files:
                    self.included_files.add(resolved_path)
                    logger.debug(f"Loading library section: {resolved_path}:{section_name}")
                    
                    try:
                        # Extract specific section from library file
                        section_content = self._extract_lib_section(
                            resolved_path, section_name
                        )
                        if section_content:
                            combined_content.append(
                                f"* BEGIN LIB: {lib_path} ({section_name})"
                            )
                            combined_content.append(section_content)
                            combined_content.append(
                                f"* END LIB: {lib_path} ({section_name})"
                            )
                        else:
                            logger.warning(
                                f"Section '{section_name}' not found in '{lib_path}'"
                            )
                            combined_content.append(line)
                    except Exception as e:
                        logger.warning(
                            f"Failed to load library '{lib_path}:{section_name}': {e}"
                        )
                        combined_content.append(line)
                else:
                    combined_content.append(f"* SKIP LIB: {lib_path} ({section_name})")
                continue
            
            # Check for include directive: .include "filename" or .inc 'filename'
            include_match = re.match(
                r'\s*\.(?:include|inc)\s+["\']([^"\']+)["\']',
                stripped,
                re.IGNORECASE,
            )
            if include_match:
                include_path = include_match.group(1)
                resolved_path = self._resolve_include_path(include_path)

                if (
                    resolved_path
                    and resolved_path not in self.included_files
                ):
                    self.included_files.add(resolved_path)
                    logger.debug(f"Loading include: {resolved_path}")

                    try:
                        # Create parser for included file
                        include_parser = HSPICEParser(resolved_path)
                        include_content = (
                            include_parser._load_with_includes()
                        )
                        combined_content.append(
                            f"* BEGIN INCLUDE: {include_path}"
                        )
                        combined_content.append(include_content)
                        combined_content.append(
                            f"* END INCLUDE: {include_path}"
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to load include '{include_path}': {e}"
                        )
                        combined_content.append(line)
                else:
                    combined_content.append(
                        f"* SKIP INCLUDE: {include_path}"
                    )
                continue
            
            # Regular line - keep as-is
            combined_content.append(line)

        return "\n".join(combined_content)
    
    def _extract_lib_section(self, lib_path: Path, section_name: str) -> Optional[str]:
        """
        Extract a specific section from an HSPICE library file.
        
        Sections are delimited by:
        - .lib section_name (start)
        - .endl [section_name] (end)
        
        Args:
            lib_path: Path to library file
            section_name: Name of section to extract
            
        Returns:
            Content of the section, or None if not found
        """
        try:
            content = lib_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            content = lib_path.read_text(encoding='latin-1')
        
        lines = content.split('\n')
        section_content = []
        in_section = False
        section_pattern = re.compile(
            rf'^\s*\.lib\s+{re.escape(section_name)}\s*$',
            re.IGNORECASE
        )
        endl_pattern = re.compile(
            rf'^\s*\.endl(\s+{re.escape(section_name)})?\s*$',
            re.IGNORECASE
        )
        
        for line in lines:
            stripped = line.strip()
            
            if not in_section:
                # Look for section start
                if section_pattern.match(stripped):
                    in_section = True
                    logger.debug(f"Found section start: {section_name}")
                    continue
            else:
                # Look for section end
                if endl_pattern.match(stripped):
                    logger.debug(f"Found section end: {section_name}")
                    break
                section_content.append(line)
        
        if section_content:
            # Recursively resolve includes within the section
            temp_content = '\n'.join(section_content)
            # Create a temporary parser to resolve nested includes
            temp_parser = HSPICEParser.__new__(HSPICEParser)
            temp_parser.file_path = lib_path
            temp_parser.content = temp_content
            temp_parser.included_files = self.included_files  # Share the set
            temp_parser.expr_parser = self.expr_parser
            return temp_parser._load_with_includes()
        
        return None
