"""
Ngspice format parser with IR output.

Parses ngspice .lib files and converts to ModelIR representation.
Handles .lib sections and .model cards similar to SPICE3.

Compliance: CONSTRAINTS.md
"""

from typing import List, Dict, Any, Optional, Set
from pathlib import Path
import re
import logging

from .base_parser import BaseParser
from .expression_parser import EnhancedExpressionParser
from ..ir.model_ir import (
    ModelIR,
    Condition,
    Corner,
    Temperature,
    DeviceType,
)

logger = logging.getLogger(__name__)


class NgspiceParser(BaseParser):
    """
    Parser for ngspice format (.lib files).

    Ngspice files use:
    - .lib <name> for library sections
    - .model <name> <type> <params> for model cards
    - + for continuation lines (optional)

    Converts ngspice models to universal IR representation.
    """

    # Continuation line indicator
    CONTINUATION_CHAR = "+"

    def __init__(self, file_path: Path) -> None:
        """
        Initialize ngspice parser.

        Args:
            file_path: Path to ngspice .lib file
        """
        super().__init__(file_path)
        self.expr_parser = EnhancedExpressionParser()
        self.current_lib: Optional[str] = None
        self.included_files: Set[Path] = set()

    def get_format_name(self) -> str:
        """
        Get format identifier.

        Returns:
            Format name 'ngspice'
        """
        return "ngspice"

    def parse_to_ir(self, follow_includes: bool = False) -> List[ModelIR]:
        """
        Parse ngspice file to IR representation.

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
            # Remove inline comments (* or $)
            if "*" in line:
                line = line.split("*")[0]
            if "$" in line:
                line = line.split("$")[0]

            stripped = line.strip()

            # Skip comment lines
            if stripped.startswith("*") or stripped.startswith("$"):
                if current_line:
                    joined_lines.append(current_line)
                    current_line = ""
                joined_lines.append(line)
                continue

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
        Extract .model cards from ngspice content.

        Args:
            content: Ngspice file content (continuation lines joined)

        Returns:
            List of model card dictionaries
        """
        cards: List[Dict[str, Any]] = []
        lines = content.split("\n")
        current_lib: Optional[str] = None

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Skip empty and comment lines
            if not stripped or stripped.startswith(("*", "$")):
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
        # Handle optional parentheses around params
        parts = line.split(None, 2)
        if len(parts) < 2:
            logger.debug(f"Invalid model card at line {line_num}: {line}")
            return None

        name = parts[0]
        model_type = parts[1]
        param_str = parts[2] if len(parts) > 2 else ""

        # Remove parentheses if present
        param_str = param_str.strip()
        if param_str.startswith("(") and param_str.endswith(")"):
            param_str = param_str[1:-1]

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
        ir_model.metadata["source_format"] = "ngspice"

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

        # Pattern for param=value
        pattern = r"(\w+)\s*=\s*([^\s]+)"

        for match in re.finditer(pattern, param_str):
            param_name = match.group(1)
            param_value_str = match.group(2)

            # Evaluate expression
            try:
                result = self.expr_parser.parse_expression(
                    param_value_str
                )
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
            name: Model name (e.g., 'nch', 'pch')
            model_type: Model type string (e.g., 'nmos', 'pmos')

        Returns:
            DeviceType enum value
        """
        name_lower = name.lower()
        type_lower = model_type.lower()

        # Direct type matching
        if type_lower in ["nmos", "nch", "nfet"]:
            return DeviceType.NMOS
        if type_lower in ["pmos", "pch", "pfet"]:
            return DeviceType.PMOS
        if type_lower in ["npn"]:
            return DeviceType.NPN
        if type_lower in ["pnp"]:
            return DeviceType.PNP

        # Name-based detection
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

        # Diode detection
        if "diode" in type_lower or "d_" in name_lower:
            return DeviceType.DIODE

        # Resistor detection
        if "resistor" in type_lower or "res" in type_lower:
            return DeviceType.RESISTOR

        # Capacitor detection
        if "capacitor" in type_lower or "cap" in type_lower:
            return DeviceType.CAPACITOR

        logger.warning(
            f"Could not classify device type for name='{name}', "
            f"type='{model_type}', defaulting to NMOS"
        )
        return DeviceType.NMOS  # Default fallback

    def _load_with_includes(self) -> str:
        """
        Load file content with include directives resolved.

        Recursively loads files referenced by .include statements.

        Returns:
            Combined content with all includes resolved
        """
        if not self.content:
            return ""

        combined_content = []
        lines = self.content.split("\n")

        for line in lines:
            # Check for include directive: .include "filename"
            match = re.match(
                r'\s*\.include\s+["\']([^"\']+)["\']',
                line,
                re.IGNORECASE,
            )
            if match:
                include_path = match.group(1)
                resolved_path = self._resolve_include_path(
                    include_path
                )

                if (
                    resolved_path
                    and resolved_path not in self.included_files
                ):
                    self.included_files.add(resolved_path)
                    logger.debug(f"Loading include: {resolved_path}")

                    try:
                        # Create parser for included file
                        include_parser = NgspiceParser(resolved_path)
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
                    # Already included or not found
                    combined_content.append(
                        f"* SKIP INCLUDE: {include_path}"
                    )
            else:
                combined_content.append(line)

        return "\n".join(combined_content)
