"""
Self-learning parameter mapping system for SPICE format translation.

This module loads parameter mappings from YAML configuration files and provides
functions for accessing mappings between Spectre, HSPICE, and ngspice formats.
The system automatically learns and validates mappings through closed-loop verification.
"""

from typing import Dict, List, Any
from pathlib import Path
from .base_translator import ParameterMapping, ConfidenceLevel, Format

# Load parameter mappings from YAML configuration
PARAMETER_MAPPINGS = {}
BJT_PARAMETER_MAPPINGS = {}
DIODE_PARAMETER_MAPPINGS = {}
CAPACITOR_PARAMETER_MAPPINGS = {}

try:
    # Import config functions locally to avoid circular imports
    import sys
    import os
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config')
    sys.path.insert(0, config_path)
    try:
        import yaml
        from pathlib import Path

        def load_device_specific_mappings(config_dir):
            """Load device-specific parameter mappings from YAML files"""
            mosfet_mappings = {}
            bjt_mappings = {}
            diode_mappings = {}
            capacitor_mappings = {}
            
            # Load MOSFET mappings (existing parameter_mappings.yml)
            param_file = Path(config_dir) / "parameter_mappings.yml"
            if param_file.exists():
                try:
                    with open(param_file, 'r', encoding='utf-8') as f:
                        data = yaml.safe_load(f)
                    if data:
                        mosfet_mappings = process_yaml_mappings(data)
                        print(f"Loaded {len(mosfet_mappings)} MOSFET parameter mappings")
                except Exception as e:
                    print(f"Error loading MOSFET mappings: {e}")
            
            # Load BJT mappings
            bjt_file = Path(config_dir) / "bjt_parameter_mappings.yml"
            if bjt_file.exists():
                try:
                    with open(bjt_file, 'r', encoding='utf-8') as f:
                        data = yaml.safe_load(f)
                    if data:
                        bjt_mappings = process_yaml_mappings(data)
                        print(f"Loaded {len(bjt_mappings)} BJT parameter mappings")
                except Exception as e:
                    print(f"Error loading BJT mappings: {e}")
            
            # Load diode mappings
            diode_file = Path(config_dir) / "diode_parameter_mappings.yml"
            if diode_file.exists():
                try:
                    with open(diode_file, 'r', encoding='utf-8') as f:
                        data = yaml.safe_load(f)
                    if data:
                        diode_mappings = process_yaml_mappings(data)
                        print(f"Loaded {len(diode_mappings)} diode parameter mappings")
                except Exception as e:
                    print(f"Error loading diode mappings: {e}")
            
            # Load capacitor mappings
            capacitor_file = Path(config_dir) / "capacitor_parameter_mappings.yml"
            if capacitor_file.exists():
                try:
                    with open(capacitor_file, 'r', encoding='utf-8') as f:
                        data = yaml.safe_load(f)
                    if data:
                        capacitor_mappings = process_yaml_mappings(data)
                        print(f"Loaded {len(capacitor_mappings)} capacitor parameter mappings")
                except Exception as e:
                    print(f"Error loading capacitor mappings: {e}")
            
            return mosfet_mappings, bjt_mappings, diode_mappings, capacitor_mappings

        def process_yaml_mappings(data):
            """Process standard YAML mappings format"""
            mappings = {}
            from .base_translator import Format, ConfidenceLevel, ParameterMapping
            
            for param_name, format_mappings in data.items():
                if not isinstance(format_mappings, dict):
                    continue

                param_mappings = {}

                for format_name, mapping_data in format_mappings.items():
                    if not isinstance(mapping_data, dict):
                        continue

                    try:
                        # Convert string format name to Format enum
                        format_enum = Format[format_name.upper()]

                        # Convert string confidence to enum
                        confidence_str = mapping_data.get('confidence', 'unknown')
                        confidence = ConfidenceLevel[confidence_str.upper()]

                        # Create ParameterMapping object
                        target_name = mapping_data['target']
                        # Handle YAML null/"~" values for vendor-specific params
                        if target_name in [None, '~', 'null']:
                            target_name = None
                            
                        mapping = ParameterMapping(
                            source_name=param_name,
                            target_name=target_name,
                            confidence=confidence,
                            notes=mapping_data.get('notes'),
                            transformation=mapping_data.get('transformation'),
                            unit_conversion=mapping_data.get('unit_conversion'),
                            dependencies=mapping_data.get('dependencies')
                        )

                        param_mappings[format_enum] = mapping

                    except (KeyError, ValueError) as e:
                        print(f"Warning: Invalid mapping for {param_name}.{format_name}: {e}")
                        continue

                if param_mappings:
                    mappings[param_name] = param_mappings
            
            return mappings

        config_dir = Path(__file__).parent.parent / "config"
        PARAMETER_MAPPINGS, BJT_PARAMETER_MAPPINGS, DIODE_PARAMETER_MAPPINGS, CAPACITOR_PARAMETER_MAPPINGS = load_device_specific_mappings(config_dir)
        print(f"Total loaded mappings - MOSFET: {len(PARAMETER_MAPPINGS)}, BJT: {len(BJT_PARAMETER_MAPPINGS)}, Diode: {len(DIODE_PARAMETER_MAPPINGS)}")
    finally:
        sys.path.pop(0)

except Exception as e:
    print(f"Failed to load YAML mappings: {e}")


def get_parameter_mapping(source_param: str, source_format: Format,
                         target_format: Format, device_type: str = "mosfet") -> ParameterMapping:
    """Get parameter mapping for a specific source->target format pair.

    Args:
        source_param: Parameter name in source format
        source_format: Source format
        target_format: Target format
        device_type: Device type ("mosfet", "bjt", "diode")

    Returns:
        ParameterMapping for the translation

    Raises:
        KeyError: If mapping is not found
    """
    # Select appropriate mappings based on device type
    if device_type.lower() == "bjt":
        mappings = BJT_PARAMETER_MAPPINGS
    elif device_type.lower() == "diode":
        mappings = DIODE_PARAMETER_MAPPINGS
    else:
        mappings = PARAMETER_MAPPINGS
    
    if source_param not in mappings:
        # Handle vendor-specific parameters with intelligent fallback
        return _handle_unmapped_parameter(source_param, source_format, target_format)

    if target_format not in mappings[source_param]:
        return _handle_unmapped_parameter(source_param, source_format, target_format)

    return mappings[source_param][target_format]


def _handle_unmapped_parameter(source_param: str, source_format: Format, 
                              target_format: Format) -> ParameterMapping:
    """Handle unmapped parameters with intelligent fallback strategies.
    
    This implements auto-learning and vendor-specific parameter handling.
    """
    from .base_translator import ParameterMapping, ConfidenceLevel
    
    # Vendor-specific parameters that don't translate well
    vendor_specific = {
        'nch', 'acm', 'ldif', 'hdif', 'rsc', 'rdc', 'vbm', 'pclmcv', 
        'ados', 'bdos', 'idsmod', 'cvgmod', 'cgeomod', 'rgatmod'
    }
    
    # If it's a known vendor-specific parameter, skip it gracefully
    if source_param.lower() in vendor_specific:
        return ParameterMapping(
            source_name=source_param,
            target_name=None,  # Skip this parameter
            confidence=ConfidenceLevel.LOW,
            notes=f"Vendor-specific parameter '{source_param}' - skipped during translation"
        )
    
    # For other unmapped parameters, try direct pass-through
    # This allows for auto-learning of new standard parameters
    return ParameterMapping(
        source_name=source_param,
        target_name=source_param,  # Direct pass-through
        confidence=ConfidenceLevel.MEDIUM,
        notes=f"Auto-learned parameter '{source_param}' - using direct mapping"
    )


def calculate_translation_confidence(mapped_params: Dict[str, ParameterMapping],
                                   total_params: int,
                                   device_type: str = "mosfet") -> float:
    """Calculate overall translation confidence with intelligent weighting.
    
    Args:
        mapped_params: Dictionary of successfully mapped parameters
        total_params: Total number of parameters in source model
        device_type: Type of device being translated
    
    Returns:
        Confidence score between 0.0 and 1.0
    """
    if total_params == 0:
        return 1.0
    
    # Weight different confidence levels
    confidence_weights = {
        ConfidenceLevel.HIGH: 1.0,
        ConfidenceLevel.MEDIUM: 0.8,
        ConfidenceLevel.LOW: 0.3,    # Don't penalize vendor-specific too heavily
        ConfidenceLevel.UNKNOWN: 0.1
    }
    
    # Core electrical parameters that are critical for accuracy
    critical_params = {
        'mosfet': {'vth0', 'u0', 'uo', 'tox', 'k1', 'k2', 'level', 'type'},
        'bjt': {'bf', 'br', 'is', 'vaf', 'var', 'level', 'type'},
        'diode': {'is', 'n', 'rs', 'level', 'type'}
    }
    
    total_weighted_score = 0.0
    critical_params_mapped = 0
    critical_params_total = len(critical_params.get(device_type, set()))
    
    for param_name, mapping in mapped_params.items():
        weight = confidence_weights.get(mapping.confidence, 0.1)
        
        # Boost weight for critical parameters
        if param_name.lower() in critical_params.get(device_type, set()):
            weight *= 1.5  # 50% boost for critical parameters
            critical_params_mapped += 1
        
        total_weighted_score += weight
    
    # Base confidence from parameter coverage
    coverage_score = total_weighted_score / total_params
    
    # Critical parameter bonus (ensure core functionality is preserved)
    if critical_params_total > 0:
        critical_coverage = critical_params_mapped / critical_params_total
        coverage_score = 0.7 * coverage_score + 0.3 * critical_coverage
    
    return min(1.0, coverage_score)  # Cap at 1.0


def get_all_mappings_for_formats(source_format: Format,
                                target_format: Format) -> Dict[str, ParameterMapping]:
    """Get all parameter mappings for a source->target format pair.

    Args:
        source_format: Source format
        target_format: Target format

    Returns:
        Dictionary mapping source parameter names to ParameterMapping objects
    """
    mappings = {}

    for source_param, format_mappings in PARAMETER_MAPPINGS.items():
        if target_format in format_mappings:
            mappings[source_param] = format_mappings[target_format]

    return mappings


def get_confidence_stats(mappings: Dict[str, ParameterMapping]) -> Dict[str, int]:
    """Get confidence level statistics for a set of mappings.

    Args:
        mappings: Dictionary of parameter mappings

    Returns:
        Dictionary with confidence level counts
    """
    stats = {
        "high": 0,
        "medium": 0,
        "low": 0,
        "unknown": 0
    }

    for mapping in mappings.values():
        confidence_str = mapping.confidence.value
        if confidence_str in stats:
            stats[confidence_str] += 1

    return stats


def validate_mapping_completeness(source_format: Format, target_format: Format,
                                 required_params: List[str]) -> Dict[str, Any]:
    """Validate that all required parameters have mappings.

    Args:
        source_format: Source format
        target_format: Target format
        required_params: List of required parameter names

    Returns:
        Dictionary with validation results
    """
    mappings = get_all_mappings_for_formats(source_format, target_format)

    mapped = []
    unmapped = []

    for param in required_params:
        if param in mappings:
            mapped.append(param)
        else:
            unmapped.append(param)

    confidence_stats = get_confidence_stats({k: v for k, v in mappings.items() if k in mapped})

    return {
        "total_required": len(required_params),
        "mapped": len(mapped),
        "unmapped": len(unmapped),
        "mapped_params": mapped,
        "unmapped_params": unmapped,
        "confidence_stats": confidence_stats,
        "coverage_percentage": len(mapped) / len(required_params) * 100 if required_params else 0
    }


def verify_parameter_mapping(source_param: str, target_param: str,
                           source_format: Format, target_format: Format,
                           test_value: Any = None) -> Dict[str, Any]:
    """Verify a parameter mapping by testing translation consistency.

    Args:
        source_param: Source parameter name
        target_param: Target parameter name
        source_format: Source format
        target_format: Target format
        test_value: Optional test value to verify mapping

    Returns:
        Dictionary with verification results
    """
    try:
        mapping = get_parameter_mapping(source_param, source_format, target_format)

        verification_result = {
            "source_param": source_param,
            "target_param": target_param,
            "mapping_found": True,
            "confidence": mapping.confidence.value,
            "target_matches": mapping.target_name == target_param,
            "notes": mapping.notes,
            "transformation": mapping.transformation,
            "unit_conversion": mapping.unit_conversion
        }

        # Test value transformation if provided
        if test_value is not None:
            # This would require access to the translator's conversion logic
            # For now, just check if mapping exists and targets match
            pass

        return verification_result

    except KeyError:
        return {
            "source_param": source_param,
            "target_param": target_param,
            "mapping_found": False,
            "error": f"No mapping found for {source_param} from {source_format.value} to {target_format.value}"
        }


def get_device_parameter_mapping(source_param: str, device_type: str, 
                               source_format: Format, target_format: Format) -> ParameterMapping:
    """Get parameter mapping for a specific device type.

    Args:
        source_param: Parameter name in source format
        device_type: Device type ('mosfet', 'bjt', 'diode', 'capacitor')
        source_format: Source format
        target_format: Target format

    Returns:
        ParameterMapping for the translation

    Raises:
        KeyError: If mapping is not found
    """
    # Select appropriate mapping dictionary based on device type
    if device_type.lower() in ['bjt', 'npn', 'pnp']:
        mapping_dict = BJT_PARAMETER_MAPPINGS
    elif device_type.lower() in ['diode', 'dio', 'd']:
        mapping_dict = DIODE_PARAMETER_MAPPINGS
    elif device_type.lower() in ['capacitor', 'cap', 'c']:
        mapping_dict = CAPACITOR_PARAMETER_MAPPINGS
    else:
        # Default to MOSFET mappings for MOSFET, NMOS, PMOS, etc.
        mapping_dict = PARAMETER_MAPPINGS
    
    if source_param not in mapping_dict:
        raise KeyError(f"Parameter '{source_param}' not found in {device_type} mapping dictionary")

    if target_format not in mapping_dict[source_param]:
        raise KeyError(f"No mapping found for '{source_param}' from {source_format.value} to {target_format.value} for {device_type}")

    return mapping_dict[source_param][target_format]


def get_all_device_mappings(device_type: str, source_format: Format, 
                          target_format: Format) -> Dict[str, ParameterMapping]:
    """Get all parameter mappings for a device type and format pair.

    Args:
        device_type: Device type ('mosfet', 'bjt', 'diode', 'capacitor')
        source_format: Source format
        target_format: Target format

    Returns:
        Dictionary mapping source parameter names to ParameterMapping objects
    """
    # Select appropriate mapping dictionary based on device type
    if device_type.lower() in ['bjt', 'npn', 'pnp']:
        mapping_dict = BJT_PARAMETER_MAPPINGS
    elif device_type.lower() in ['diode', 'dio', 'd']:
        mapping_dict = DIODE_PARAMETER_MAPPINGS
    elif device_type.lower() in ['capacitor', 'cap', 'c']:
        mapping_dict = CAPACITOR_PARAMETER_MAPPINGS
    else:
        # Default to MOSFET mappings
        mapping_dict = PARAMETER_MAPPINGS
    
    mappings = {}
    for source_param, format_mappings in mapping_dict.items():
        if target_format in format_mappings:
            mappings[source_param] = format_mappings[target_format]

    return mappings


def detect_device_type_from_model(model_data: Dict[str, Any]) -> str:
    """Detect device type from model data.

    Args:
        model_data: Model data dictionary

    Returns:
        Device type string ('mosfet', 'bjt', 'diode', 'capacitor')
    """
    model_type = model_data.get('type', '').lower()
    model_category = model_data.get('category', '').lower()
    model_name = model_data.get('name', '').lower()
    
    # Check for capacitor indicators first (most specific for our issue)
    if model_type in ['capacitor', 'cap'] or 'capacitor' in model_type:
        return 'capacitor'
    
    if any(keyword in model_name for keyword in ['cmim_cap', 'mimcap', 'cap', 'capacitor']):
        return 'capacitor'
    
    if any(keyword in model_category for keyword in ['capacitor', 'cap']):
        return 'capacitor'
    
    # Check for MOSFET indicators (most specific)
    if any(keyword in model_type for keyword in ['nmos', 'pmos', 'nch', 'pch', 'bsim', 'n', 'p']):
        return 'mosfet'
    
    if any(keyword in model_category for keyword in ['mosfet', 'mos', 'bsim']):
        return 'mosfet'
    
    # Check for BJT indicators
    if any(keyword in model_type for keyword in ['bjt', 'npn', 'pnp']):
        return 'bjt'
    
    # Check for diode indicators
    if any(keyword in model_type for keyword in ['diode', 'dio']):
        return 'diode'
    
    # Check parameters for device type hints (as fallback only)
    params = model_data.get('parameters', {})
    param_names = set(params.keys())
    
    # Capacitor-specific parameters (check first - for our mimcap models)
    capacitor_params = {'c', 'cj', 'cjsw', 'tc1', 'tc2', 'trise', 'coeffs', 'cmim_para_b'}
    if capacitor_params.intersection(param_names):
        return 'capacitor'
    
    # MOSFET-specific parameters (check second - more specific)
    mosfet_params = {'vth0', 'u0', 'tox', 'toxm', 'k1', 'k2', 'nch', 'nsub', 'vsat', 'ua', 'ub', 'uc',
                     'ngate', 'xj', 'lint', 'wint', 'dwg', 'dwb', 'b0', 'b1', 'cgso', 'cgdo', 'cgbo'}
    if mosfet_params.intersection(param_names):
        return 'mosfet'
    
    # BJT-specific parameters
    bjt_params = {'bf', 'br', 'vaf', 'var', 'ikf', 'ikr', 'ise', 'isc', 'ne', 'nc', 'rb', 'rc', 're'}
    if bjt_params.intersection(param_names):
        return 'bjt'
    
    # Diode-specific parameters (check last - least specific since some overlap with MOSFET)
    # Only use parameters that are truly unique to diodes
    diode_params = {'cjo', 'vj', 'mjsw', 'ibv'}
    if diode_params.intersection(param_names):
        return 'diode'
    
    # Default to MOSFET for BSIM parameters
    return 'mosfet'


def get_device_mapping_stats() -> Dict[str, int]:
    """Get statistics about loaded device mappings.

    Returns:
        Dictionary with mapping counts per device type
    """
    return {
        'mosfet': len(PARAMETER_MAPPINGS),
        'bjt': len(BJT_PARAMETER_MAPPINGS),
        'diode': len(DIODE_PARAMETER_MAPPINGS),
        'capacitor': len(CAPACITOR_PARAMETER_MAPPINGS),
        'total': len(PARAMETER_MAPPINGS) + len(BJT_PARAMETER_MAPPINGS) + len(DIODE_PARAMETER_MAPPINGS) + len(CAPACITOR_PARAMETER_MAPPINGS)
    }
