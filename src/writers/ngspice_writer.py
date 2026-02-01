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

        # Group models by section (Spectre sections map to ngspice .lib blocks)
        section_groups = self._group_by_section(models)

        # Generate content
        content_lines = [header]

        # Write models without section (base models)
        if None in section_groups:
            base_models = section_groups[None]
            if base_models:
                content_lines.append("* Base models (no corner/section variations)")
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
                    if not (model.subcircuits and model.subcircuits and 
                            'area' in model.subcircuits[0].parameters):
                        content_lines.append(self._format_model(model, None))
                        content_lines.append("")

        # Write section-specific models (corners from Spectre sections)
        # NOTE: ngspice doesn't support .lib/.endl blocks like HSPICE
        # Use comments to separate sections; users should include only what they need
        written_models = set()  # Track what we've written to avoid duplicates
        
        for section_name in sorted(section_groups.keys()):
            if section_name is None:
                continue
                
            section_models = section_groups[section_name]
            
            # Add section comment separator
            content_lines.append(f"* =========== Section: {section_name} ===========")
            content_lines.append("")

            # Write parameters from section
            if section_models and hasattr(section_models[0], 'metadata'):
                section_params = section_models[0].metadata.get('section_params', {})
                if section_params:
                    for pname, pval in section_params.items():
                        content_lines.append(f".param {pname}={pval}")
                    content_lines.append("")

            for model in section_models:
                # Skip if already written (avoid duplicates from section nesting)
                model_key = model.name if hasattr(model, 'name') else id(model)
                if model_key in written_models:
                    continue
                written_models.add(model_key)
                
                # Write subcircuits
                if model.subcircuits:
                    for subckt in model.subcircuits:
                        subckt_key = subckt.name
                        if subckt_key in written_models:
                            continue
                        written_models.add(subckt_key)
                        
                        content_lines.extend(
                            self._format_subcircuit(subckt, model.statistical)
                        )
                        content_lines.append("")
                
                # Write model card if needed
                if not (model.subcircuits and model.subcircuits and 
                        'area' in model.subcircuits[0].parameters):
                    content_lines.append(self._format_model(model, None))
                    content_lines.append("")

            content_lines.append("")

        # Write to file
        content = "\n".join(content_lines)
        self._write_content(content)
        logger.info(
            f"Wrote {len(models)} models to {self.output_path.name}"
        )

    def _group_by_section(
        self, models: List[ModelIR]
    ) -> Dict[Optional[str], List[ModelIR]]:
        """
        Group models by Spectre section name.
        
        Spectre sections (res_t, res_l, res_h) map to ngspice .lib blocks.

        Args:
            models: List of ModelIR objects

        Returns:
            Dictionary mapping section names to models (None = no section)
        """
        section_groups: Dict[Optional[str], List[ModelIR]] = {}

        for model in models:
            # Get section from metadata
            section = model.metadata.get('section', None) if hasattr(model, 'metadata') else None
            
            if section not in section_groups:
                section_groups[section] = []
            section_groups[section].append(model)

        return section_groups

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
            "RESISTOR": "R",
            "CAPACITOR": "capacitor",
        }

        device_str = str(model.device_type).split(".")[-1]
        
        # Special handling for rdiff and other resistor subtypes
        if model.model_type and 'rdiff' in model.model_type.lower():
            return "R"
        if model.model_type and 'res' in model.model_type.lower():
            return "R"
        if model.model_type and 'phy_res' in model.model_type.lower():
            return "R"
        
        return device_map.get(device_str, model.model_type if model.model_type else "R")

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
            # For inline subcircuits, extract default parameters from declaration
            default_params = {}
            for element in subckt.elements:
                # Parse parameter lines like "l = 0.6e-6 \"
                if '=' in element and not element.strip().startswith('.'):
                    parts = element.split('=', 1)
                    if len(parts) == 2:
                        pname = parts[0].strip()
                        pval = parts[1].strip().rstrip('\\')
                        if pname and not pname[0].isdigit():
                            default_params[pname] = pval
            
            # Build subcircuit header with default parameters
            ports_str = " ".join(subckt.ports)
            # Track which parameters are input parameters (from subcircuit header)
            # Only include basic geometric/instance parameters, not calculated ones
            input_param_names = ['l', 'w', 'simM', 'dtemp', 'm', 'mult']
            input_params = set()
            
            if default_params:
                # Extract input defaults for header
                geom_defaults = []
                for key in input_param_names:
                    if key in default_params:
                        geom_defaults.append(f"{key}={default_params[key]}")
                        input_params.add(key)  # Track as input param
                
                if geom_defaults:
                    params_str = " ".join(geom_defaults)
                    lines.append(f".subckt {subckt.name} {ports_str} {params_str}")
                else:
                    lines.append(f".subckt {subckt.name} {ports_str}")
            else:
                lines.append(f".subckt {subckt.name} {ports_str}")
            
            # Convert elements to proper ngspice syntax
            
            instance_counter = {'R': 0, 'C': 0, 'M': 0, 'X': 0}
            
            for element in subckt.elements:
                element = element.strip().rstrip('\\')
                
                # Skip empty lines
                if not element:
                    continue
                
                # Check if this is a model definition
                if element.startswith('model '):
                    # Format: model <name> <type> <params>
                    parts = element.split(None, 2)
                    if len(parts) >= 2:
                        model_name = parts[1]
                        rest = parts[2] if len(parts) > 2 else ""
                        lines.append(f".model {model_name} R ({rest})")
                    continue
                
                # Check if this is a device instance line
                # Pattern: <instance_name> <space> (nodes...) <model_name> <params>
                # Must have space before opening paren and paren must be early in line
                words = element.split()
                paren_start = element.find('(')
                
                # Device instance has form: "name (nodes) model params"
                # Parameter has form: "name = expression (with parens)"
                # Key difference: device has '(' before '=', parameter has '=' before '('
                is_device_instance = False
                if len(words) >= 2 and paren_start > 0:
                    # Check if '(' appears before any '=' sign
                    equals_pos = element.find('=')
                    if equals_pos == -1 or paren_start < equals_pos:
                        # This is likely a device instance
                        is_device_instance = True
                
                if is_device_instance:
                    # This looks like: gpdk090_ressndiff (PLUS MINUS B) ressndiff l=l w=w_mc
                    # Extract: instance_name (nodes) model params
                    paren_end = element.find(')')
                    
                    if paren_start > 0 and paren_end > paren_start:
                        # Get nodes between parentheses
                        nodes_str = element[paren_start+1:paren_end].strip()
                        # Get model and params after closing paren
                        after_paren = element[paren_end+1:].strip()
                        model_and_params = after_paren.split(None, 1)
                        
                        if model_and_params:
                            model_name = model_and_params[0]
                            params = model_and_params[1] if len(model_and_params) > 1 else ""
                            
                            # Determine device type from model name
                            if 'res' in model_name.lower() or 'rdiff' in model_name.lower():
                                dev_type = 'R'
                            elif 'cap' in model_name.lower():
                                dev_type = 'C'
                            elif 'mos' in model_name.lower():
                                dev_type = 'M'
                            else:
                                dev_type = 'X'
                            
                            # Create instance name
                            instance_counter[dev_type] += 1
                            inst_name = f"{dev_type}{instance_counter[dev_type]}"
                            
                            # Wrap parameter values in {}
                            param_parts = params.split()
                            formatted_params = []
                            for p in param_parts:
                                if '=' in p:
                                    k, v = p.split('=', 1)
                                    # Wrap in {} if it's a variable reference or expression
                                    if v and not v[0].isdigit() and v[0] != '-':
                                        formatted_params.append(f"{k}={{{v}}}")
                                    else:
                                        formatted_params.append(p)
                                else:
                                    formatted_params.append(p)
                            
                            params_str = " ".join(formatted_params) if formatted_params else ""
                            lines.append(f"{inst_name} {nodes_str} {model_name} {params_str}")
                        continue
                
                # Check if this is a parameter definition
                if '=' in element:
                    parts = element.split('=', 1)
                    if len(parts) == 2:
                        pname = parts[0].strip()
                        pval = parts[1].strip()
                        
                        # Skip if this is an input parameter (already in .subckt header)
                        if pname in input_params:
                            continue
                        
                        # Skip device instance lines (format: X1 nodes model params)
                        if pname and (pname[0].isalpha() and len(pname) > 1 and pname[1].isdigit()):
                            continue
                        
                        # This is a calculated parameter - use .param with {}
                        if pname and not pname[0].isdigit():
                            # Wrap expressions in {}
                            if any(op in pval for op in ['*', '/', '+', '-', 'sqrt', '(', 'pres_mc', 'triseRes']):
                                lines.append(f"+ .param {pname} = {{{pval}}}")
                            else:
                                lines.append(f"+ .param {pname} = {{{pval}}}")
                        continue
                
                # Handle any other elements
                if element and not element.startswith('.'):
                    lines.append(f"+ {element}")
        
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
