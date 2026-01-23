"""
Ngspice format writer for IR output.

Converts ModelIR representation to ngspice .lib format.
Handles .lib sections and .model cards with SPICE3 compatibility.

Compliance: CONSTRAINTS.md
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import logging

from .base_writer import BaseWriter
from ..ir.model_ir import ModelIR, Corner, Temperature
from ..lowering.capacitor_lowering import CapacitorLowering
from ..lowering.backend_capabilities import BackendCapabilities

logger = logging.getLogger(__name__)


class NgspiceWriter(BaseWriter):
    """
    Writer for ngspice format (.lib files).

    Converts universal IR to ngspice .lib sections with .model cards.
    Compatible with SPICE3 syntax.
    """

    def __init__(self, output_path: Path) -> None:
        """
        Initialize ngspice writer.

        Args:
            output_path: Path where ngspice file will be written
        """
        super().__init__(output_path)
        self.lowering = CapacitorLowering(backend='ngspice')
        self.capabilities = BackendCapabilities.get('ngspice')

    def get_format_name(self) -> str:
        """
        Get format identifier.

        Returns:
            Format name 'ngspice'
        """
        return "ngspice"

    def write_from_ir(
        self, models: List[ModelIR], comment_char: str = "*"
    ) -> None:
        """
        Write IR models to ngspice format file.

        Args:
            models: List of ModelIR objects to write
            comment_char: Comment character for header (default: *)

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
            content_lines.append("* Base models (no corner variations)")
            content_lines.append("")
            
            for model in base_models:
                # Write subcircuits first (with statistical support)
                if model.subcircuits:
                    for subckt in model.subcircuits:
                        # Pass statistical block to enable MC in lowering
                        content_lines.extend(
                            self._format_subcircuit(subckt, model.statistical)
                        )
                        content_lines.append("")
                
                # Write usage instructions if statistical modeling present
                if model.statistical:
                    content_lines.extend(self._format_statistical(model.statistical))
                    content_lines.append("")
                
                # Skip .model output - capacitor is fully lowered to primitives
                # Only write .model if not a lowered capacitor
                if not (model.subcircuits and 'area' in model.subcircuits[0].parameters):
                    content_lines.append(self._format_model(model, None))
                    content_lines.append("")

        # Write corner-specific lib sections
        for corner in [Corner.TT, Corner.FF, Corner.SS, Corner.FS, Corner.SF]:
            if corner in corner_groups:
                section_models = corner_groups[corner]
                content_lines.append(f".lib {corner.name.lower()}")
                content_lines.append("")

                for model in section_models:
                    content_lines.append(
                        self._format_model(model, corner)
                    )
                    content_lines.append("")

                content_lines.append(".endl")
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
        Format a single model as ngspice .model card.

        Args:
            model: ModelIR object to format
            corner: Corner for variation, or None for base params

        Returns:
            Formatted ngspice model string
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

        # Format device type for ngspice
        device_type = self._get_ngspice_type(model)

        # Build parameter string
        param_strs = []
        for key, value in sorted(params.items()):
            param_strs.append(f"{key}={self._format_value(value)}")

        params_str = " ".join(param_strs)

        # Format: .model <name> <type> (params)
        if params_str:
            return f".model {model.name} {device_type} ({params_str})"
        else:
            return f".model {model.name} {device_type}"

    def _get_ngspice_type(self, model: ModelIR) -> str:
        """
        Get ngspice device type string.

        Args:
            model: ModelIR object

        Returns:
            Ngspice type string (nmos, pmos, npn, pnp, etc.)
        """
        device_map = {
            "NMOS": "nmos",
            "PMOS": "pmos",
            "NPN": "npn",
            "PNP": "pnp",
            "DIODE": "diode",
            "RESISTOR": "resistor",
            "CAPACITOR": "capacitor",
        }

        device_str = str(model.device_type).split(".")[-1]
        return device_map.get(device_str, model.model_type)

    def _format_value(self, value: Any) -> str:
        """
        Format a parameter value for ngspice syntax.

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
            # Return as-is (already formatted)
            return value
        else:
            return str(value)

    def _format_subcircuit(self, subckt, statistical=None) -> List[str]:
        """
        Format a subcircuit definition for ngspice with lowering.
        
        Args:
            subckt: SubcircuitIR object
            statistical: StatisticalBlock (optional)
            
        Returns:
            List of formatted lines
        """
        lines = []
        lines.append(f"* Subcircuit: {subckt.name}")
        
        # Check if this needs lowering (capacitor with area/perim)
        needs_lowering = (
            'area' in subckt.parameters and 
            'perim' in subckt.parameters
        )
        
        if needs_lowering:
            # Apply lowering pass
            lowered = self.lowering.lower_capacitor(
                subckt.name,
                subckt.ports,
                subckt.parameters,
                subckt.elements,
                statistical
            )
            
            # Format lowered version
            # Geometry parameters are subcircuit arguments (not .param)
            geom_args = []
            for param in ['area', 'perim']:
                if param in lowered.geometry_params:
                    default = lowered.geometry_params[param]
                    geom_args.append(f"{param}={default}")
            
            ports_str = " ".join(subckt.ports)
            args_str = " ".join(geom_args)
            lines.append(f".subckt {subckt.name} {ports_str} {args_str}")
            lines.append("")
            
            # Add comments
            lines.append("* Geometry scaling")
            
            # Parameters
            for param in lowered.parameters:
                lines.append(param)
            
            # Functions
            if lowered.functions:
                lines.append("")
                for func in lowered.functions:
                    lines.append(func)
            
            lines.append("")
            lines.append("* Capacitance elements (area + sidewall)")
            
            # Area capacitor
            if lowered.area_capacitor:
                lines.append(lowered.area_capacitor)
            
            # Sidewall capacitor
            if lowered.sidewall_capacitor:
                lines.append(lowered.sidewall_capacitor)
            
            # Series resistor
            if lowered.series_resistor:
                lines.append("")
                lines.append("* Series resistance")
                lines.append(lowered.series_resistor)
            
        else:
            # No lowering needed - format normally
            ports_str = " ".join(subckt.ports)
            lines.append(f".subckt {subckt.name} {ports_str}")
            
            # Parameters
            if subckt.parameters:
                for pname, pval in subckt.parameters.items():
                    lines.append(f".param {pname}={pval}")
            
            # Elements
            for element in subckt.elements:
                element = element.replace("resistor", "")
                lines.append(f"  {element}")
        
        # End subcircuit
        lines.append(f".ends {subckt.name}")
        
        return lines
    
    def _format_statistical(self, stats) -> List[str]:
        """
        Format statistical block as ngspice usage instructions.
        
        NOTE: Statistical modeling is now embedded in subcircuit via lowering.
        This provides usage instructions only.
        
        Args:
            stats: StatisticalBlock object
            
        Returns:
            List of formatted lines
        """
        lines = []
        lines.append("* Monte Carlo Analysis Instructions")
        lines.append("* ====================================")
        lines.append("*")
        lines.append("* The subcircuit above includes Monte Carlo support via:")
        lines.append("*   .param mc_en=0    (Monte Carlo enable: 0=off, 1=on)")
        lines.append("*   .func mc_gauss()  (Gaussian random number generator)")
        lines.append("*")
        lines.append("* To run Monte Carlo analysis:")
        lines.append("*   1. Enable: .param mc_en=1")
        lines.append("*   2. Run: .control")
        lines.append("*           mcruns = 100")
        lines.append("*           let mc_run = 0")
        lines.append("*           dowhile mc_run < mcruns")
        lines.append("*             ac dec 10 1 1e9")
        lines.append("*             let mc_run = mc_run + 1")
        lines.append("*           end")
        lines.append("*           .endc")
        lines.append("*")
        
        # Add corner variation instructions
        lines.append("* Corner Analysis Instructions")
        lines.append("* ==============================")
        lines.append("*")
        lines.append("* Process corners via cap_var parameter:")
        lines.append("*   Typical: .param cap_var=1.0")
        lines.append("*   Low:     .param cap_var=0.9")
        lines.append("*   High:    .param cap_var=1.1")
        
        return lines
