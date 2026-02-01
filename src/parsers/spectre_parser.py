"""
Spectre format parser with IR output.

Parses Cadence Spectre .scs files and converts to ModelIR representation.
Handles section-based corner organization and nested parameter blocks.

Compliance: CONSTRAINTS.md
"""

from typing import List, Dict, Any, Optional, Set
from pathlib import Path
import re
import logging

from .base_parser import BaseParser
from .expression_parser import EnhancedExpressionParser
from .param_parsing import parse_param_string
from ..ir.model_ir import (
    ModelIR,
    SubcircuitIR,
    StatisticalBlock,
    Condition,
    Corner,
    Temperature,
    DeviceType,
)

logger = logging.getLogger(__name__)


class SpectreParser(BaseParser):
    """
    Parser for Cadence Spectre format (.scs files).

    Spectre files use section-based organization:
    - section tt { ... } for TT corner
    - model <name> <type> { params } for model definitions

    Converts Spectre models to universal IR representation.
    """

    def __init__(self, file_path: Path) -> None:
        """
        Initialize Spectre parser.

        Args:
            file_path: Path to Spectre .scs file
        """
        super().__init__(file_path)
        self.expr_parser = EnhancedExpressionParser()
        self.current_section: Optional[str] = None
        self.included_files: Set[Path] = set()

    def get_format_name(self) -> str:
        """
        Get format identifier.

        Returns:
            Format name 'spectre'
        """
        return "spectre"

    def parse_to_ir(self, follow_includes: bool = False) -> List[ModelIR]:
        """
        Parse Spectre file to IR representation.

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

        # Extract various components
        model_blocks = self._extract_model_blocks(content)
        subcircuits = self.extract_subcircuits(content)
        sections = self.extract_sections(content)
        statistics = self.extract_statistics(content)

        # Convert each block to IR
        ir_models: List[ModelIR] = []
        for block in model_blocks:
            try:
                ir_model = self._block_to_ir(block)
                if ir_model:
                    # Attach subcircuits
                    ir_model.subcircuits = subcircuits
                    
                    # Attach statistical data
                    if statistics:
                        ir_model.statistical = statistics
                    
                    # Add corner variations from sections
                    section = block.get("section")
                    if section and section in sections:
                        section_params = sections[section]
                        # Store section parameters as metadata
                        ir_model.metadata['section'] = section
                        ir_model.metadata['section_params'] = section_params
                    
                    ir_models.append(ir_model)
            except Exception as e:
                logger.warning(
                    f"Error converting block '{block.get('name', 'unknown')}' "
                    f"to IR: {e}"
                )
                continue

        # If no models but we have standalone subcircuits, convert them to ModelIR
        # This handles files that only contain subcircuit wrappers
        if not ir_models and subcircuits:
            logger.debug(f"No models found, converting {len(subcircuits)} subcircuits to IR")
            for subckt in subcircuits:
                ir_model = self._subcircuit_to_ir(subckt)
                if ir_model:
                    # Attach statistical data if available
                    if statistics:
                        ir_model.statistical = statistics
                    ir_models.append(ir_model)

        logger.info(
            f"Parsed {len(ir_models)} models from {self.file_path.name}"
        )
        return ir_models
    
    def _subcircuit_to_ir(self, subckt: SubcircuitIR) -> Optional[ModelIR]:
        """
        Convert standalone subcircuit to ModelIR representation.
        
        Args:
            subckt: SubcircuitIR object
            
        Returns:
            ModelIR or None if conversion fails
        """
        try:
            # Classify device type from subcircuit name
            device_type = self._classify_device_type(subckt.name, "subcircuit")
            
            # Create IR model
            ir_model = ModelIR(
                name=subckt.name,
                device_type=device_type,
                model_type="subcircuit",
            )
            ir_model.metadata["source_format"] = "spectre"
            ir_model.metadata["is_subcircuit"] = True
            ir_model.metadata["ports"] = subckt.ports
            
            # Use subcircuit parameters as base parameters
            ir_model.base_parameters = subckt.parameters
            
            # Attach the subcircuit itself
            ir_model.subcircuits = [subckt]
            
            logger.debug(f"Converted subcircuit '{subckt.name}' to ModelIR")
            return ir_model
            
        except Exception as e:
            logger.warning(f"Error converting subcircuit '{subckt.name}' to IR: {e}")
            return None

    def _extract_model_blocks(
        self, content: str
    ) -> List[Dict[str, Any]]:
        """
        Extract model blocks from Spectre content.

        Handles section organization and nested braces.

        Args:
            content: Spectre file content

        Returns:
            List of model block dictionaries
        """
        blocks: List[Dict[str, Any]] = []
        lines = content.split("\n")
        i = 0
        current_section: Optional[str] = None

        while i < len(lines):
            line = lines[i].strip()

            # Remove comments
            if "//" in line:
                line = line.split("//")[0].strip()

            # Skip empty lines
            if not line:
                i += 1
                continue

            # Track section boundaries
            if line.startswith("section "):
                match = re.match(r"section\s+(\w+)", line)
                if match:
                    current_section = match.group(1)
                    logger.debug(f"Entering section: {current_section}")
                i += 1
                continue

            elif line.startswith("endsection"):
                logger.debug(f"Exiting section: {current_section}")
                current_section = None
                i += 1
                continue

            # Model block: model <name> <type> { ... }
            if line.startswith("model "):
                block = self._extract_single_block(
                    lines, i, current_section
                )
                if block:
                    blocks.append(block)
                    i = block["end_line"]
                else:
                    i += 1
            else:
                i += 1

        logger.debug(f"Extracted {len(blocks)} model blocks")
        return blocks

    def _extract_single_block(
        self,
        lines: List[str],
        start: int,
        section: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        """
        Extract single model block with parameters.
        
        Supports two formats:
        1. Inline: model name type param1=val1 param2=val2
        2. Braced: model name type { params }

        Args:
            lines: All file lines
            start: Start line index
            section: Current section name (corner)

        Returns:
            Block dictionary with name, type, params, or None if invalid
        """
        # Parse header: model nch bsim4 { OR model name type params
        header = lines[start].strip()

        # Remove inline comments
        if "//" in header:
            header = header.split("//")[0].strip()

        # Match: model <name> <type> <rest>
        match = re.match(r"model\s+(\w+)\s+(\w+)\s*(.*)", header)

        if not match:
            logger.debug(f"Invalid model header at line {start}: {header}")
            return None

        name = match.group(1)
        model_type = match.group(2)
        remainder = match.group(3).strip()

        # Determine format: braced vs inline
        if remainder.startswith("{") or "{" in remainder:
            # Braced format - use existing logic
            return self._extract_braced_model(
                lines, start, name, model_type, section, header
            )
        elif remainder:
            # Inline format with parameters on same line
            return self._extract_inline_model(
                name, model_type, remainder, section, start
            )
        else:
            # No parameters
            return {
                "name": name,
                "type": model_type,
                "param_lines": [],
                "section": section,
                "start_line": start,
                "end_line": start + 1,
            }

    def _extract_inline_model(
        self,
        name: str,
        model_type: str,
        param_string: str,
        section: Optional[str],
        start: int,
    ) -> Dict[str, Any]:
        """
        Extract model with inline parameters on single line.
        
        Example: model gpdk090_mimcap_x capacitor cj=1e-3 cjsw=1e-10
        
        Args:
            name: Model name
            model_type: Device type
            param_string: String containing param=value pairs
            section: Current section name
            start: Start line number
            
        Returns:
            Block dictionary with extracted parameters
        """
        param_lines = [param_string] if param_string else []
        
        logger.debug(f"Extracted inline model '{name}' with {len(param_string)} chars of parameters")
        
        return {
            "name": name,
            "type": model_type,
            "param_lines": param_lines,
            "section": section,
            "start_line": start,
            "end_line": start + 1,
        }

    def _extract_braced_model(
        self,
        lines: List[str],
        start: int,
        name: str,
        model_type: str,
        section: Optional[str],
        header: str,
    ) -> Dict[str, Any]:
        """
        Extract model with braced parameters.
        
        Example:
            model nch bsim4 {
              vth0=0.4
              tox=2e-9
            }
        
        Args:
            lines: All file lines
            start: Start line
            name: Model name
            model_type: Device type
            section: Current section
            header: First line content
            
        Returns:
            Block dictionary
        """
        param_lines: List[str] = []
        brace_count = header.count("{") - header.count("}")
        
        # If braces are balanced on first line, extract params from header
        if brace_count == 0 and "{" in header:
            # Extract content between { }
            content_match = re.search(r"\{([^}]*)\}", header)
            if content_match:
                param_content = content_match.group(1).strip()
                if param_content:
                    param_lines.append(param_content)
            return {
                "name": name,
                "type": model_type,
                "param_lines": param_lines,
                "section": section,
                "start_line": start,
                "end_line": start + 1,
            }
        
        # Multi-line case
        i = start + 1

        while i < len(lines) and brace_count > 0:
            line = lines[i].strip()

            # Remove comments
            if "//" in line:
                line = line.split("//")[0].strip()

            # Count braces
            brace_count += line.count("{")
            brace_count -= line.count("}")

            if brace_count > 0 and line:
                param_lines.append(line)

            i += 1

        return {
            "name": name,
            "type": model_type,
            "param_lines": param_lines,
            "section": section,
            "start_line": start,
            "end_line": i,
        }

    def _block_to_ir(
        self, block: Dict[str, Any]
    ) -> Optional[ModelIR]:
        """
        Convert parsed block to ModelIR.

        Args:
            block: Block dictionary from _extract_single_block

        Returns:
            ModelIR object or None if conversion fails
        """
        name = block["name"]
        model_type = block["type"]
        param_lines = block["param_lines"]
        section = block.get("section")

        # Classify device type
        device_type = self._classify_device_type(name, model_type)

        # Parse parameters
        parameters = self._parse_parameters(param_lines)

        # Create IR model
        ir_model = ModelIR(
            name=name,
            device_type=device_type,
            model_type=model_type,
        )
        ir_model.metadata["source_format"] = "spectre"

        # If in a section, create variation
        if section:
            try:
                # Try to parse section as corner
                corner = Corner.from_string(section.upper())
                condition = Condition(
                    corner=corner, temperature=Temperature.NOMINAL
                )

                ir_model.add_variation(
                    condition=condition,
                    parameters=parameters,
                    source_line=block["start_line"],
                    source_file=str(self.file_path),
                )

            except ValueError:
                # Not a standard corner, use as base parameters
                logger.debug(
                    f"Section '{section}' not a standard corner, "
                    f"using as base parameters"
                )
                ir_model.base_parameters = parameters
        else:
            # No section, use as base parameters
            ir_model.base_parameters = parameters

        return ir_model

    def _parse_parameters(
        self, param_lines: List[str]
    ) -> Dict[str, Any]:
        """
        Parse parameter lines into key-value dictionary.

        Args:
            param_lines: Lines containing parameter assignments

        Returns:
            Parameter dictionary with evaluated values
        """
        parameters: Dict[str, Any] = {}

        for line in param_lines:
            raw_params = parse_param_string(line)
            for param_name, raw_value in raw_params.items():
                param_value_str = raw_value.strip().rstrip(",;")
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
            name: Model name (e.g., 'nch', 'pch')
            model_type: Model type string (e.g., 'bsim4')

        Returns:
            DeviceType enum value
        """
        name_lower = name.lower()
        type_lower = model_type.lower()

        # MOSFET detection by name
        if any(
            x in name_lower
            for x in ["nch", "nmos", "nfet", "nwell"]
        ):
            return DeviceType.NMOS
        if any(
            x in name_lower
            for x in ["pch", "pmos", "pfet", "pwell"]
        ):
            return DeviceType.PMOS

        # Model type-based detection
        if any(
            x in type_lower
            for x in ["bsim", "psp", "mos", "mosfet"]
        ):
            # Default to NMOS if 'n' in name, otherwise PMOS
            return (
                DeviceType.NMOS
                if "n" in name_lower[:2]
                else DeviceType.PMOS
            )

        # BJT detection
        if any(x in type_lower for x in ["bjt", "vbic", "mextram"]):
            return (
                DeviceType.NPN
                if "npn" in name_lower
                else DeviceType.PNP
            )

        # Diode detection
        if "diode" in type_lower or "diode" in name_lower:
            return DeviceType.DIODE

        # Resistor detection
        if any(
            x in type_lower for x in ["resistor", "res", "r2_cmo"]
        ):
            return DeviceType.RESISTOR

        # Capacitor detection
        if any(x in type_lower for x in ["capacitor", "cap", "c_"]):
            return DeviceType.CAPACITOR

        logger.warning(
            f"Could not classify device type for name='{name}', "
            f"type='{model_type}'"
        )
        return DeviceType.NMOS  # Default fallback

    def _load_with_includes(self) -> str:
        """
        Load file content with include directives resolved.

        Recursively loads files referenced by include statements.

        Returns:
            Combined content with all includes resolved
        """
        if not self.content:
            return ""

        combined_content = []
        lines = self.content.split("\n")

        for line in lines:
            # Check for include directive: include "filename"
            match = re.match(r'\s*include\s+"([^"]+)"', line)
            if match:
                include_path = match.group(1)
                resolved_path = self._resolve_include_path(
                    include_path
                )

                if resolved_path and resolved_path not in self.included_files:
                    self.included_files.add(resolved_path)
                    logger.debug(f"Loading include: {resolved_path}")

                    try:
                        # Create parser for included file
                        include_parser = SpectreParser(resolved_path)
                        include_content = include_parser._load_with_includes()
                        combined_content.append(
                            f"// BEGIN INCLUDE: {include_path}"
                        )
                        combined_content.append(include_content)
                        combined_content.append(
                            f"// END INCLUDE: {include_path}"
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to load include '{include_path}': {e}"
                        )
                        combined_content.append(line)
                else:
                    # Already included or not found
                    combined_content.append(
                        f"// SKIP INCLUDE: {include_path}"
                    )
            else:
                combined_content.append(line)

        return "\n".join(combined_content)

    def _resolve_include_path(self, include_path: str) -> Optional[Path]:
        """Resolve include file path relative to current file."""
        if Path(include_path).is_absolute():
            return Path(include_path)
        return self.file_path.parent / include_path

    def extract_subcircuits(self, content: str) -> List[SubcircuitIR]:
        """
        Extract subcircuit definitions from Spectre content.
        
        Handles both formats:
        1. inline subckt gpdk090_mimcap (P M) ...
        2. subckt gpdk090_nmos1v_iso (n1 n2 n3 n4 n5) ...
        
        Args:
            content: Spectre file content
            
        Returns:
            List of SubcircuitIR objects
        """
        subcircuits = []
        lines = content.split("\n")
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Remove comments
            if "//" in line:
                line = line.split("//")[0].strip()
            
            # Match: inline subckt <name> (<ports>) OR subckt <name> (<ports>)
            if re.match(r"(inline\s+)?subckt\s+", line):
                subckt = self._extract_subcircuit_block(lines, i)
                if subckt:
                    subcircuits.append(subckt)
                    i = subckt.metadata.get('end_line', i + 1)
                else:
                    i += 1
            else:
                i += 1
        
        logger.debug(f"Extracted {len(subcircuits)} subcircuits")
        return subcircuits
    
    def _extract_subcircuit_block(
        self, lines: List[str], start: int
    ) -> Optional[SubcircuitIR]:
        """Extract single subcircuit block."""
        header = lines[start].strip()
        
        # Parse: [inline] subckt name (port1 port2 ...)
        match = re.match(
            r"(?:inline\s+)?subckt\s+(\w+)\s*\(([^)]+)\)", header
        )
        if not match:
            return None
        
        name = match.group(1)
        ports = [p.strip() for p in match.group(2).split()]
        
        # Extract content until 'ends'
        parameters = {}
        elements = []
        models_used = []
        i = start + 1
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Remove comments
            if "//" in line:
                line = line.split("//")[0].strip()
            
            if not line:
                i += 1
                continue
            
            # End of subcircuit
            if line.startswith("ends"):
                break
            
            # Parameters line
            if line.startswith("parameters"):
                params_str = line.replace("parameters", "").strip()
                for pname, pval in parse_param_string(params_str).items():
                    parameters[pname] = pval.strip().rstrip(",;")
            else:
                # Element line - extract model references
                elements.append(line)
                # Extract model name from device instance lines
                # Format: INSTANCE_NAME (nodes) MODEL_NAME params
                elem_match = re.match(r"(\w+)\s+\([^)]+\)\s+(\w+)", line)
                if elem_match:
                    model_name = elem_match.group(2)
                    if model_name not in models_used:
                        models_used.append(model_name)
            
            i += 1
        
        subckt = SubcircuitIR(
            name=name,
            ports=ports,
            parameters=parameters,
            elements=elements,
            models_used=models_used
        )
        subckt.metadata['start_line'] = start
        subckt.metadata['end_line'] = i + 1
        
        logger.debug(f"Extracted subcircuit '{name}' with {len(ports)} ports, {len(elements)} elements")
        return subckt
    
    def extract_sections(self, content: str) -> Dict[str, Dict[str, Any]]:
        """
        Extract section blocks with parameter overrides for corners.
        
        Example:
            section cap_l
              parameters cap_var=0.9
            endsection cap_l
        
        Args:
            content: Spectre file content
            
        Returns:
            Dictionary mapping section name to parameters
        """
        sections = {}
        lines = content.split("\n")
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Remove comments
            if "//" in line:
                line = line.split("//")[0].strip()
            
            # Match: section <name>
            match = re.match(r"section\s+(\w+)", line)
            if match:
                section_name = match.group(1)
                params = self._extract_section_parameters(lines, i)
                sections[section_name] = params
                logger.debug(f"Extracted section '{section_name}' with {len(params)} parameters")
            
            i += 1
        
        return sections
    
    def _extract_section_parameters(
        self, lines: List[str], start: int
    ) -> Dict[str, Any]:
        """Extract parameters from section block."""
        parameters = {}
        i = start + 1
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Remove comments
            if "//" in line:
                line = line.split("//")[0].strip()
            
            if line.startswith("endsection"):
                break
            
            # Parameters line
            if line.startswith("parameters"):
                params_str = line.replace("parameters", "").strip()
                # Handle continuation with +
                while params_str.endswith("+") and i + 1 < len(lines):
                    i += 1
                    params_str = params_str[:-1] + " " + lines[i].strip()

                for pname, pval in parse_param_string(params_str).items():
                    parameters[pname] = pval.strip().rstrip(",;")
            
            i += 1
        
        return parameters
    
    def extract_statistics(self, content: str) -> Optional[StatisticalBlock]:
        """
        Extract statistical modeling blocks.
        
        Example:
            statistics {
              mismatch {
                vary pc_mc dist=gauss std=1/1
              }
            }
        
        Args:
            content: Spectre file content
            
        Returns:
            StatisticalBlock or None if no statistics found
        """
        lines = content.split("\n")
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Remove comments
            if "//" in line:
                line = line.split("//")[0].strip()
            
            # Match: statistics {
            if re.match(r"statistics\s*\{", line):
                return self._extract_statistics_block(lines, i)
            
            i += 1
        
        return None
    
    def _extract_statistics_block(
        self, lines: List[str], start: int
    ) -> StatisticalBlock:
        """Extract statistical block content."""
        variables = {}
        mismatch_params = {}
        brace_count = 1
        i = start + 1
        current_block = None
        
        while i < len(lines) and brace_count > 0:
            line = lines[i].strip()
            
            # Remove comments
            if "//" in line:
                line = line.split("//")[0].strip()
            
            brace_count += line.count("{")
            brace_count -= line.count("}")
            
            # Match: mismatch {
            if re.match(r"mismatch\s*\{", line):
                current_block = "mismatch"
            
            # Match: vary variable dist=distribution std=value
            match = re.match(
                r"vary\s+(\w+)\s+dist=(\w+)\s+std=([^\s]+)", line
            )
            if match:
                var_name = match.group(1)
                distribution = match.group(2)
                std_dev = match.group(3)
                
                variables[var_name] = {
                    'distribution': distribution,
                    'std': std_dev,
                    'block': current_block
                }
                
                logger.debug(
                    f"Extracted statistical variable '{var_name}' "
                    f"dist={distribution} std={std_dev}"
                )
            
            i += 1
        
        stat_block = StatisticalBlock(
            variables=variables,
            mismatch_params=mismatch_params
        )
        stat_block.metadata['start_line'] = start
        stat_block.metadata['end_line'] = i
        
        return stat_block
