"""
Spectre format writer for IR output.

Converts ModelIR representation to Cadence Spectre .scs format.
Handles section-based corner organization.

Compliance: CONSTRAINTS.md
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import logging

from .base_writer import BaseWriter
from ..ir.model_ir import ModelIR, Corner, Temperature
from ..lowering.backend_capabilities import BackendCapabilities

logger = logging.getLogger(__name__)


class SpectreWriter(BaseWriter):
    """
    Writer for Cadence Spectre format (.scs files).

    Converts universal IR to Spectre section-based format with
    corner organization (section tt { }, section ff { }, etc.).
    """

    def __init__(self, output_path: Path) -> None:
        """
        Initialize Spectre writer.

        Args:
            output_path: Path where Spectre file will be written
        """
        super().__init__(output_path)
        self.capabilities = BackendCapabilities.get('spectre')
        # Spectre supports native models - no lowering needed

    def get_format_name(self) -> str:
        """
        Get format identifier.

        Returns:
            Format name 'spectre'
        """
        return "spectre"

    def write_from_ir(
        self, models: List[ModelIR], comment_char: str = "//"
    ) -> None:
        """
        Write IR models to Spectre format file.

        Args:
            models: List of ModelIR objects to write
            comment_char: Comment character for header (default: //)

        Raises:
            ValueError: If models list is empty or invalid
        """
        if not self.validate_models(models):
            raise ValueError("Invalid models provided")

        # Generate header
        header = self._generate_header(comment_char)

        # Group models by corner
        corner_groups = self._group_by_corner(models)

        # Generate content
        content_lines = [header]

        # Write models without corner variations first
        base_models = [m for m in models if not m.has_variations()]
        if base_models:
            content_lines.append("// Base models (no corner variations)")
            for model in base_models:
                # Write subcircuits (Spectre native format)
                if model.subcircuits:
                    for subckt in model.subcircuits:
                        content_lines.append(self._format_subcircuit(subckt))
                        content_lines.append("")
                
                # Write statistical blocks (Spectre native format)
                if model.statistical:
                    content_lines.append(self._format_statistical(model.statistical))
                    content_lines.append("")
                
                # Write model
                content_lines.append(self._format_model(model, None))
                content_lines.append("")

        # Write corner-specific sections
        for corner in [Corner.TT, Corner.FF, Corner.SS, Corner.FS, Corner.SF]:
            if corner in corner_groups:
                section_models = corner_groups[corner]
                content_lines.append(f"section {corner.name.lower()} {{")
                content_lines.append("")

                for model in section_models:
                    content_lines.append(
                        self._format_model(model, corner)
                    )
                    content_lines.append("")

                content_lines.append("}")
                content_lines.append("")

        # Write to file
        content = "\n".join(content_lines)
        self._write_content(content)
        logger.info(
            f"Wrote {len(models)} models to {self.output_path.name}"
        )

    def _group_by_corner(
        self, models: List[ModelIR]
    ) -> Dict[Corner, List[ModelIR]]:
        """
        Group models by corner variation.

        Args:
            models: List of ModelIR objects

        Returns:
            Dictionary mapping corners to models
        """
        corner_groups: Dict[Corner, List[ModelIR]] = {}

        for model in models:
            if model.has_variations():
                for condition in model.get_conditions():
                    corner = condition.corner
                    if corner not in corner_groups:
                        corner_groups[corner] = []
                    corner_groups[corner].append(model)

        return corner_groups

    def _format_model(
        self, model: ModelIR, corner: Optional[Corner]
    ) -> str:
        """
        Format a single model as Spectre syntax.

        Args:
            model: ModelIR object to format
            corner: Corner for variation, or None for base params

        Returns:
            Formatted Spectre model string
        """
        # Get parameters for this corner
        if corner is not None:
            # Get variation parameters
            condition = None
            for cond in model.get_conditions():
                if cond.corner == corner:
                    condition = cond
                    break

            if condition:
                variation = model.get_variation(condition)
                params = variation.parameters if variation else {}
            else:
                params = {}
        else:
            # Use base parameters
            params = model.base_parameters

        # Format: model <name> <type> { <params> }
        lines = [f"model {model.name} {model.model_type} {{"]

        # Add parameters
        if params:
            for key, value in sorted(params.items()):
                lines.append(f"    {key} = {self._format_value(value)}")

        lines.append("}")

        return "\n".join(lines)

    def _format_value(self, value: Any) -> str:
        """
        Format a parameter value for Spectre syntax.

        Args:
            value: Parameter value to format

        Returns:
            Formatted value string
        """
        if isinstance(value, bool):
            return "1" if value else "0"
        elif isinstance(value, (int, float)):
            # Use scientific notation for very small/large numbers
            if isinstance(value, float):
                if abs(value) < 1e-3 or abs(value) > 1e6:
                    return f"{value:.6e}"
                else:
                    return str(value)
            return str(value)
        elif isinstance(value, str):
            v = value.strip()
            # If value is quoted (often HSPICE-style), strip the outer quotes so Spectre can treat it as an expression.
            if (
                len(v) >= 2
                and v[0] == v[-1]
                and v[0] in ("'", '"')
            ):
                v = v[1:-1].strip()
            # If it's numeric, keep as-is
            try:
                float(v)
                return v
            except ValueError:
                pass

            # If it looks like an expression, keep unquoted.
            if any(op in v for op in ("+", "-", "*", "/", "(", ")", "{", "}", "?", ":")):
                return v

            # Otherwise treat as a string literal.
            return f'"{v}"'
        else:
            return str(value)

    def _format_subcircuit(self, subckt) -> str:
        """
        Format a subcircuit in Spectre native format.
        
        Spectre supports native subcircuits with inline syntax.
        No lowering needed - preserve original format.
        
        Args:
            subckt: SubcircuitIR object
            
        Returns:
            Formatted subcircuit string
        """
        lines = []
        
        # Inline subcircuit definition
        ports_str = " ".join(subckt.ports)
        lines.append(f"inline subckt {subckt.name} ({ports_str})")
        
        # Parameters
        if subckt.parameters:
            params = " ".join(f"{k}={v}" for k, v in subckt.parameters.items())
            lines.append(f"    parameters {params}")
        
        # Elements
        for element in subckt.elements:
            lines.append(f"    {element}")
        
        lines.append(f"ends {subckt.name}")
        
        return "\n".join(lines)
    
    def _format_statistical(self, stats) -> str:
        """
        Format statistical block in Spectre native format.
        
        Spectre has native statistics { } blocks - preserve them.
        
        Args:
            stats: StatisticalBlock object
            
        Returns:
            Formatted statistics string
        """
        lines = []
        lines.append("statistics {")
        lines.append("    mismatch {")
        
        for var_name, var_info in stats.variables.items():
            dist = var_info.get('distribution', 'gauss')
            std = var_info.get('std', '1')
            lines.append(f"        vary {var_name} dist={dist} std={std}")
        
        lines.append("    }")
        lines.append("}")
        
        return "\n".join(lines)
