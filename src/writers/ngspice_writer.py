"""
Ngspice format writer for IR output.

Converts ModelIR representation to ngspice .lib format.
Handles .lib sections and .model cards with SPICE3 compatibility.

Compliance: CONSTRAINTS.md
"""

from typing import List, Dict, Any, Optional
from pathlib import Path
import logging
import re

from .base_writer import BaseWriter
from ..ir.model_ir import ModelIR, Corner, Temperature, DeviceType
from ..lowering.capacitor_lowering import CapacitorLowering
from ..lowering.backend_capabilities import BackendCapabilities

logger = logging.getLogger(__name__)


class NgspiceWriter(BaseWriter):
    """
    Writer for ngspice format (.lib files).

    Converts universal IR to ngspice .lib sections with .model cards.
    Compatible with SPICE3 syntax.
    """

    # Soft limit to keep .model lines readable and avoid simulator line-length issues.
    MAX_LINE_LENGTH = 120

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

        # Emit default parameters for expressions so ngspice can evaluate them.
        # Many HSPICE model decks use symbolic deltas (e.g. dbf_*) inside expressions.
        # Without defaults, ngspice will often error out on 'unknown parameter'.
        expr_symbols = self._collect_expression_symbols(models)
        model_names_lower = {m.name.lower() for m in models if getattr(m, "name", None)}
        expr_symbols = {
            s
            for s in expr_symbols
            if s.lower() not in model_names_lower
        }
        if expr_symbols:
            content_lines.append("* Auto-generated parameter defaults (override as needed)")
            # Heuristic defaults: most symbolic *multipliers* should default to 1,
            # while true deltas/offsets default to 0. This keeps models from
            # degenerating into all-zeros (which can cause OP convergence issues)
            # while still preventing undefined-parameter errors.
            default_one = {
                # Common Spectre/HSPICE scaling factors in this corpus
                'cbeta', 'cis', 'cvaf', 'ctf', 'ccj', 'ccjd', 'crsd', 'pis_mc', 'pisd_mc', 'geo_fac',
            }
            suffix_one_re = re.compile(r"_(?:npn|pnp|nmos|pmos)$", flags=re.IGNORECASE)
            for sym in sorted(expr_symbols):
                if suffix_one_re.search(sym) or sym.lower() in default_one:
                    content_lines.append(f".param {sym}=1")
                else:
                    content_lines.append(f".param {sym}=0")
            content_lines.append("")

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

    def _collect_expression_symbols(self, models: List[ModelIR]) -> set[str]:
        """Collect symbols referenced in non-numeric parameter expressions.

        This is a best-effort helper to make generated ngspice decks runnable.
        We only emit defaults for symbols found in string-valued parameters that
        are not pure numbers.
        """

        ident_re = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")
        # Consider a value an "expression" only if it was explicitly marked
        # (brace/quoted) or contains operators/whitespace/parentheses.
        expr_hint_re = re.compile(r"[+\-*/^(),]|\s")
        builtins = {
            # Common math functions
            "sqrt",
            "log",
            "ln",
            "exp",
            "abs",
            "min",
            "max",
            "pow",
            "sin",
            "cos",
            "tan",
            "asin",
            "acos",
            "atan",
        }

        # Common non-numeric enums/tokens that should NOT be treated as
        # parameter references.
        excluded_idents = {
            "npn",
            "pnp",
            "nmos",
            "pmos",
            "n",
            "p",
            "yes",
            "no",
            "true",
            "false",
            "on",
            "off",
        }

        assign_re = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*=\s*")

        def split_assignments(text: str) -> List[tuple[str, str]]:
            matches = list(assign_re.finditer(text))
            if not matches:
                return []
            out: List[tuple[str, str]] = []
            for i, m in enumerate(matches):
                name = m.group(1)
                start = m.end()
                end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
                value = text[start:end].strip()
                out.append((name, value))
            return out

        def iter_param_values(m: ModelIR) -> List[str]:
            vals: List[str] = []

            def add_from_dict(d: Optional[Dict[str, Any]]) -> None:
                if not d:
                    return
                for v in d.values():
                    if isinstance(v, str):
                        vals.append(v)

            add_from_dict(getattr(m, "base_parameters", None))

            # Include corner/section variations, if present
            if m.has_variations():
                for cond in m.get_conditions():
                    var = m.get_variation(cond)
                    if var is not None:
                        add_from_dict(getattr(var, "parameters", None))

            # Include any extracted Spectre section parameters
            if hasattr(m, "metadata"):
                sp = m.metadata.get("section_params")
                if isinstance(sp, dict):
                    add_from_dict(sp)

            # Include subcircuit parameter defaults
            for subckt in getattr(m, "subcircuits", []) or []:
                add_from_dict(getattr(subckt, "parameters", None))

                # Also include values referenced inside subcircuit bodies.
                # Many Spectre inline subckts carry expressions on continuation
                # lines that otherwise become raw element strings in IR.
                for el in getattr(subckt, "elements", []) or []:
                    if not isinstance(el, str):
                        continue
                    txt = el.strip().rstrip('\\')
                    if not txt or '=' not in txt:
                        continue
                    # Strip leading '+' continuation for parsing only.
                    if txt.startswith('+'):
                        txt = txt.lstrip('+').strip()
                    for _, pval in split_assignments(txt):
                        if pval:
                            vals.append(pval)

            return vals

        symbols: set[str] = set()
        for model in models:
            for v in iter_param_values(model):
                if not isinstance(v, str):
                    continue

                s = v.strip()
                if not s:
                    continue

                # Bare identifiers (e.g. dagetime_r) are parameter references in ngspice.
                # Include them unless they look like enumerated tokens.
                if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", s):
                    low = s.lower()
                    if low not in builtins and low not in excluded_idents and s not in {"e", "E"}:
                        symbols.add(s)
                    continue

                looks_braced = len(s) >= 2 and s[0] == "{" and s[-1] == "}"
                looks_quoted = len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"')
                looks_expression = looks_braced or looks_quoted or bool(expr_hint_re.search(s))
                if not looks_expression:
                    # Plain tokens like 'npn'/'pnp' or 'yes' are not expressions.
                    continue

                # Strip outer quotes
                if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
                    s = s[1:-1].strip()

                # Strip outer braces
                if len(s) >= 2 and s[0] == "{" and s[-1] == "}":
                    s = s[1:-1].strip()

                # If it's numeric, no symbols needed
                try:
                    float(s)
                    continue
                except ValueError:
                    pass

                for ident in ident_re.findall(s):
                    low = ident.lower()
                    if low in builtins:
                        continue
                    if low in excluded_idents:
                        continue
                    if ident in {"e", "E"}:
                        continue
                    symbols.add(ident)

        return symbols

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

        # ngspice model cards generally do not support string-valued parameters.
        # Some upstream sources use enumerated tokens like `type=npn/pnp` which
        # ngspice interprets as an undefined parameter reference. The model type
        # itself already encodes NPN vs PNP, so drop these.
        if model.device_type in (DeviceType.NPN, DeviceType.PNP, DeviceType.NMOS, DeviceType.PMOS) and params:
            params = {k: v for k, v in params.items() if k.lower() not in {"type"}}

        # Format device type for ngspice
        device_type = self._get_ngspice_type(model)

        # Build parameter tokens
        param_tokens = [
            f"{key}={self._format_value(value)}" for key, value in sorted(params.items())
        ]

        if not param_tokens:
            return f".model {model.name} {device_type}"

        # Emit multi-line .model with continuation to avoid huge single lines.
        # ngspice supports '+' continuation.
        lines: List[str] = []
        base = f".model {model.name} {device_type} ("
        current = base

        for tok in param_tokens:
            sep = "" if current.endswith("(") else " "
            candidate = f"{current}{sep}{tok}"
            if len(candidate) > self.MAX_LINE_LENGTH and current != base:
                lines.append(current)
                current = f"+{tok}"
            else:
                current = candidate

        # Close parens on the final line
        current = f"{current})"
        lines.append(current)
        return "\n".join(lines)

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
            "DIODE": "D",
            "RESISTOR": "R",
            "CAPACITOR": "C",
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
            v = value.strip()

            # Normalize common boolean/enumerated tokens used in some Spectre decks.
            # ngspice does not treat 'yes'/'no' as literals inside expressions.
            low_v = v.lower()
            if low_v in {"yes", "true", "on"}:
                return "1"
            if low_v in {"no", "false", "off"}:
                return "0"

            def strip_unmatched_trailing_parens(expr: str) -> str:
                s = expr.strip()
                # Only strip trailing ')' if there are more ')' than '(' overall.
                # This fixes common parse artifacts like '... )' without harming
                # properly balanced expressions like 'foo*(bar)'.
                while s.endswith(')') and s.count(')') > s.count('('):
                    s = s[:-1].rstrip()
                return s

            # Guard against a common parsing artifact where the final ')'
            # from a .model card is accidentally captured as part of a numeric
            # parameter value (e.g., "version=106.1 )").
            if re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?\s*\)", v):
                v = v.rsplit(")", 1)[0].strip()

            # SPICE numeric literals can include scale suffixes (e.g., 1u, 10k).
            # Keep them as-is.
            if re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?[A-Za-z]+", v):
                return v

            # If already brace-wrapped expression, keep it but sanitize common
            # unmatched trailing parens inside the braces.
            if len(v) >= 2 and v[0] == "{" and v[-1] == "}":
                inner_raw = v[1:-1].strip()
                inner_low = inner_raw.lower()
                if inner_low in {"yes", "true", "on"}:
                    return "1"
                if inner_low in {"no", "false", "off"}:
                    return "0"
                inner = strip_unmatched_trailing_parens(inner_raw)
                return "{" + inner + "}"

            # Convert quoted expressions (common in HSPICE) into ngspice brace expressions.
            # Example:  '105.0*(1+drb)'  -> {105.0*(1+drb)}
            if (
                len(v) >= 2
                and v[0] == v[-1]
                and v[0] in ("'", '"')
            ):
                inner = v[1:-1].strip()
                inner = strip_unmatched_trailing_parens(inner)
                return "{" + inner + "}"

            # If it's numeric, keep as-is.
            try:
                float(v)
                return v
            except ValueError:
                pass

            # Bare identifiers are treated as parameter references in ngspice.
            # Use braces so substitution/expressions work consistently.
            if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", v):
                return "{" + v + "}"

            # Treat anything else non-numeric as an expression.
            v = strip_unmatched_trailing_parens(v)
            return "{" + v + "}"
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

            # Join Spectre '+' continuations for parsing.
            joined_elements: List[str] = []
            for element in subckt.elements:
                line = element.strip().rstrip('\\')
                if not line:
                    continue
                if line.startswith('+') and joined_elements:
                    joined_elements[-1] = joined_elements[-1].rstrip() + " " + line.lstrip('+').strip()
                else:
                    joined_elements.append(line)
            
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
            
            instance_counter = {'R': 0, 'C': 0, 'M': 0, 'X': 0, 'D': 0, 'Q': 0}

            # Pre-scan for local Spectre model definitions to choose proper
            # instance primitive letters when converting Spectre inline subckts.
            model_kind_by_name: dict[str, str] = {}
            for element in joined_elements:
                raw_el = element.strip().rstrip('\\')
                if not raw_el or not raw_el.lower().startswith('model '):
                    continue
                parts = raw_el.split(None, 3)
                if len(parts) >= 3:
                    model_name = parts[1]
                    spectre_type = parts[2].lower()
                    if spectre_type == 'bjt':
                        model_kind_by_name[model_name] = 'Q'
                    elif spectre_type == 'diode':
                        model_kind_by_name[model_name] = 'D'
                    elif spectre_type == 'capacitor':
                        model_kind_by_name[model_name] = 'C'
                    elif spectre_type in ('resistor', 'rdiff', 'res'):
                        model_kind_by_name[model_name] = 'R'
                    elif spectre_type in ('mos', 'nmos', 'pmos'):
                        model_kind_by_name[model_name] = 'M'
            
            assign_re = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*=\s*")

            def split_assignments(text: str) -> List[tuple[str, str]]:
                matches = list(assign_re.finditer(text))
                if not matches:
                    return []
                out: List[tuple[str, str]] = []
                for i, m in enumerate(matches):
                    name = m.group(1)
                    start = m.end()
                    end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
                    value = text[start:end].strip()
                    out.append((name, value))
                return out

            for element in joined_elements:
                element = element.strip().rstrip('\\')

                # Strip Spectre-style continuation markers for parsing.
                raw = element
                
                # Skip empty lines
                if not raw:
                    continue
                
                # Check if this is a model definition
                if raw.lower().startswith('model '):
                    # Spectre: model <name> <type> <params>
                    parts = raw.split(None, 3)
                    if len(parts) >= 3:
                        model_name = parts[1]
                        spectre_type = parts[2]
                        params = parts[3] if len(parts) > 3 else ""

                        st = spectre_type.lower()
                        params_clean = " ".join(params.split())

                        def format_model_params(text: str) -> str:
                            assigns = split_assignments(text)
                            if not assigns:
                                return ""
                            toks: List[str] = []
                            for k, v in assigns:
                                toks.append(f"{k}={self._format_value(v)}")
                            return " ".join(toks)

                        if st == 'bjt':
                            m = re.search(r"\btype\s*=\s*(npn|pnp)\b", params_clean, flags=re.IGNORECASE)
                            bjt_type = (m.group(1).lower() if m else 'npn')
                            params_clean = re.sub(
                                r"\btype\s*=\s*(npn|pnp)\b", "", params_clean, flags=re.IGNORECASE
                            )
                            params_clean = " ".join(params_clean.split())
                            formatted = format_model_params(params_clean)
                            if formatted:
                                lines.append(f".model {model_name} {bjt_type} ({formatted})")
                            else:
                                lines.append(f".model {model_name} {bjt_type}")
                        elif st == 'diode':
                            # ngspice diode model card type is typically 'D'
                            formatted = format_model_params(params_clean)
                            if formatted:
                                lines.append(f".model {model_name} D ({formatted})")
                            else:
                                lines.append(f".model {model_name} D")
                        elif st == 'capacitor':
                            # ngspice capacitor model card type is 'C'
                            formatted = format_model_params(params_clean)
                            if formatted:
                                lines.append(f".model {model_name} C ({formatted})")
                            else:
                                lines.append(f".model {model_name} C")
                        elif st in ('bsim3v3', 'bsim4', 'bsim3', 'bsim'):
                            # BSIM MOSFET models - determine nmos/pmos from type param or name
                            m = re.search(r"\btype\s*=\s*(n|p)\b", params_clean, flags=re.IGNORECASE)
                            if m:
                                mos_type = 'nmos' if m.group(1).lower() == 'n' else 'pmos'
                            elif 'nmos' in model_name.lower() or 'nch' in model_name.lower():
                                mos_type = 'nmos'
                            elif 'pmos' in model_name.lower() or 'pch' in model_name.lower():
                                mos_type = 'pmos'
                            else:
                                # Default to nmos if 'n' appears early in name
                                mos_type = 'nmos' if 'n' in model_name.lower()[:5] else 'pmos'
                            
                            # Remove the 'type=n/p' from params since it's now in the model type
                            params_clean = re.sub(
                                r"\btype\s*=\s*(n|p)\b", "", params_clean, flags=re.IGNORECASE
                            )
                            params_clean = " ".join(params_clean.split())
                            
                            # Set level based on BSIM version (BSIM3v3=8, BSIM4=14)
                            bsim_level = 8 if '3' in st else 14
                            
                            formatted = format_model_params(params_clean)
                            if formatted:
                                lines.append(f".model {model_name} {mos_type} (level={bsim_level} {formatted})")
                            else:
                                lines.append(f".model {model_name} {mos_type} (level={bsim_level})")
                        elif st in ('resistor', 'res', 'rdiff', 'phy_res'):
                            # Resistor models
                            formatted = format_model_params(params_clean)
                            if formatted:
                                lines.append(f".model {model_name} R ({formatted})")
                            else:
                                lines.append(f".model {model_name} R")
                        else:
                            # Best-effort fallback: try to determine type from model name
                            if 'res' in model_name.lower() or 'rdiff' in model_name.lower():
                                formatted = format_model_params(params_clean)
                                if formatted:
                                    lines.append(f".model {model_name} R ({formatted})")
                                else:
                                    lines.append(f".model {model_name} R")
                            elif 'mos' in model_name.lower() or 'nch' in model_name.lower() or 'pch' in model_name.lower():
                                # MOSFET - determine type from name
                                if 'nmos' in model_name.lower() or 'nch' in model_name.lower():
                                    mos_type = 'nmos'
                                elif 'pmos' in model_name.lower() or 'pch' in model_name.lower():
                                    mos_type = 'pmos'
                                else:
                                    mos_type = 'nmos' if 'n' in model_name.lower()[:5] else 'pmos'
                                formatted = format_model_params(params_clean)
                                if formatted:
                                    lines.append(f".model {model_name} {mos_type} (level=14 {formatted})")
                                else:
                                    lines.append(f".model {model_name} {mos_type} (level=14)")
                            else:
                                # Unknown type - keep as generic with warning comment
                                rest = (spectre_type + " " + params).strip()
                                lines.append(f"* WARNING: Unknown model type '{spectre_type}' - needs manual review")
                                lines.append(f".model {model_name} nmos ({rest})")
                    continue
                
                # Check if this is a device instance line
                # Pattern: <instance_name> <space> (nodes...) <model_name> <params>
                # Must have space before opening paren and paren must be early in line
                words = raw.split()
                paren_start = raw.find('(')
                
                # Device instance has form: "name (nodes) model params"
                # Parameter has form: "name = expression (with parens)"
                # Key difference: device has '(' before '=', parameter has '=' before '('
                is_device_instance = False
                if len(words) >= 2 and paren_start > 0:
                    # Check if '(' appears before any '=' sign
                    equals_pos = raw.find('=')
                    if equals_pos == -1 or paren_start < equals_pos:
                        # This is likely a device instance
                        is_device_instance = True
                
                if is_device_instance:
                    # This looks like: gpdk090_ressndiff (PLUS MINUS B) ressndiff l=l w=w_mc
                    # Extract: instance_name (nodes) model params
                    paren_end = raw.find(')')
                    
                    if paren_start > 0 and paren_end > paren_start:
                        # Get nodes between parentheses
                        nodes_str = raw[paren_start+1:paren_end].strip()
                        # Get model and params after closing paren
                        after_paren = raw[paren_end+1:].strip()
                        model_and_params = after_paren.split(None, 1)
                        
                        if model_and_params:
                            model_name = model_and_params[0]
                            params = model_and_params[1] if len(model_and_params) > 1 else ""

                            model_name_low = model_name.lower()

                            # Spectre primitive instances use a type token (e.g. 'resistor')
                            # rather than a separate model name. Convert those to ngspice
                            # primitive syntax where the value is the 4th field.
                            if model_name_low in ('resistor', 'res', 'r'):
                                assigns = {k.lower(): v for k, v in split_assignments(params)}
                                r_expr = assigns.get('r')
                                if not r_expr:
                                    # Fallback: if no explicit r=, pick a safe value.
                                    r_expr = '1'
                                instance_counter['R'] += 1
                                inst_name = f"R{instance_counter['R']}"
                                lines.append(f"{inst_name} {nodes_str} {self._format_value(r_expr)}")
                                continue

                            if model_name_low in ('capacitor', 'cap', 'c'):
                                assigns = {k.lower(): v for k, v in split_assignments(params)}
                                c_expr = assigns.get('c')
                                if not c_expr:
                                    c_expr = '1p'
                                instance_counter['C'] += 1
                                inst_name = f"C{instance_counter['C']}"
                                lines.append(f"{inst_name} {nodes_str} {self._format_value(c_expr)}")
                                continue
                            
                            # Determine device type from model name
                            dev_type = model_kind_by_name.get(model_name)
                            if not dev_type:
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
                if '=' in raw:
                    assigns = split_assignments(raw)
                    if assigns:
                        for pname, pval in assigns:
                            # Skip if this is an input parameter (already in .subckt header)
                            if pname in input_params:
                                continue

                            # Skip device instance lines (format: X1 nodes model params)
                            if pname and (pname[0].isalpha() and len(pname) > 1 and pname[1].isdigit()):
                                continue

                            if pname and not pname[0].isdigit():
                                lines.append(f".param {pname}={self._format_value(pval)}")
                        continue
                
                # Handle any other elements
                if raw and not raw.startswith('.'):
                    lines.append(raw)
        
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
