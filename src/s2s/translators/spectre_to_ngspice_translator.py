#!/usr/bin/env python3
"""
Spectre to ngspice translator implementation.

This module provides translation from Spectre (.scs) format to ngspice (.lib) format.
"""

from typing import Dict, Any, List, Tuple
import logging
from .base_translator import BaseTranslator, Format, TranslationError
from .parameter_mappings import get_all_mappings_for_formats

logger = logging.getLogger(__name__)


class SpectreToNgspiceTranslator(BaseTranslator):
    """Translator for converting Spectre models to ngspice format."""

    def __init__(self) -> None:
        """Initialize Spectre to ngspice translator."""
        super().__init__(Format.SPECTRE, Format.NGSPICE)

    def _load_parameter_mappings(self) -> None:
        """Load parameter mappings for Spectre to ngspice translation."""
        from .parameter_mappings import get_all_mappings_for_formats
        
        self.parameter_mappings = get_all_mappings_for_formats(
            Format.SPECTRE, Format.NGSPICE
        )
        logger.info(f"Loaded {len(self.parameter_mappings)} parameter mappings for Spectre->ngspice")

    def translate_model(self, model_data: Dict[str, Any]) -> Dict[str, Any]:
        """Translate a single Spectre model to ngspice format.

        Args:
            model_data: Parsed Spectre model data

        Returns:
            Translated model data in ngspice format

        Raises:
            TranslationError: If translation fails
        """
        try:
            # Extract model information
            model_name = model_data.get('name', 'unknown_model')
            model_type = model_data.get('type', 'nmos')
            model_category = model_data.get('category', 'unknown')

            # Detect device type from model data
            device_type = self._detect_device_type(model_data)
            
            # Handle device-specific translation logic
            if device_type == 'bjt':
                return self._translate_bjt_model(model_data)
            elif device_type == 'diode':
                return self._translate_diode_model(model_data)
            elif device_type == 'capacitor':
                return self._translate_capacitor_model(model_data)
            else:
                # Default MOSFET/BSIM4 handling
                return self._translate_mosfet_model(model_data)

        except Exception as e:
            error_msg = f"Failed to translate Spectre model '{model_data.get('name', 'unknown')}' to ngspice: {str(e)}"
            logger.error(error_msg)
            raise TranslationError(error_msg) from e

    def _detect_device_type(self, model_data: Dict[str, Any]) -> str:
        """Detect device type from model data.
        
        Args:
            model_data: Model data dictionary
            
        Returns:
            Device type string ('mosfet', 'bjt', 'diode')
        """
        try:
            from .parameter_mappings import detect_device_type_from_model
            return detect_device_type_from_model(model_data)
        except ImportError:
            # Fallback device detection
            model_name = model_data.get('name', '').lower()
            model_type = model_data.get('type', '').lower()
            
            if any(keyword in model_name + model_type for keyword in ['bjt', 'npn', 'pnp']):
                return 'bjt'
            elif any(keyword in model_name + model_type for keyword in ['diode', 'dio']):
                return 'diode'
            else:
                return 'mosfet'

    def _translate_bjt_model(self, model_data: Dict[str, Any]) -> Dict[str, Any]:
        """Translate BJT model from Spectre to ngspice format.
        
        Args:
            model_data: Spectre BJT model data
            
        Returns:
            Translated ngspice BJT model
        """
        from .parameter_mappings import get_device_parameter_mapping, get_all_device_mappings
        
        model_name = model_data.get('name', 'unknown_bjt')
        model_type = model_data.get('type', 'bjt')
        
        # Determine BJT type (NPN or PNP)
        bjt_type = self._determine_bjt_type(model_data)
        
        # Create ngspice BJT model structure
        ngspice_model = {
            'name': model_name,
            'type': bjt_type,  # 'npn' or 'pnp'
            'category': 'bjt',
            'level': 1,  # Standard BJT model level
            'parameters': {},
            'comments': model_data.get('comments', [])
        }

        # Translate parameters using BJT-specific mappings
        original_params = model_data.get('parameters', {})
        translated_params = {}

        for param_name, param_value in original_params.items():
            try:
                # Get BJT-specific parameter mapping
                mapping = get_device_parameter_mapping(param_name, 'bjt', Format.SPECTRE, Format.NGSPICE)
                target_name = mapping.target_name
                converted_value = self._convert_parameter_value(param_value, mapping)
                translated_params[target_name] = converted_value
                logger.debug(f"BJT: Mapped '{param_name}' -> '{target_name}': {param_value} -> {converted_value}")
            except KeyError:
                # Keep unmapped parameters as-is with warning
                if isinstance(param_value, dict) and 'value' in param_value:
                    translated_params[param_name] = param_value['value']
                else:
                    translated_params[param_name] = param_value
                logger.warning(f"No BJT mapping found for parameter '{param_name}' in model {model_name}")

        ngspice_model['parameters'] = translated_params
        logger.info(f"Translated BJT model '{model_name}' to ngspice format with type '{bjt_type}'")
        return ngspice_model

    def _translate_diode_model(self, model_data: Dict[str, Any]) -> Dict[str, Any]:
        """Translate diode model from Spectre to ngspice format.
        
        Args:
            model_data: Spectre diode model data
            
        Returns:
            Translated ngspice diode model
        """
        from .parameter_mappings import get_device_parameter_mapping, get_all_device_mappings
        
        model_name = model_data.get('name', 'unknown_diode')
        
        # Create ngspice diode model structure
        ngspice_model = {
            'name': model_name,
            'type': 'd',  # Diode type in ngspice
            'category': 'diode',
            'level': 1,  # Standard diode model level
            'parameters': {},
            'comments': model_data.get('comments', [])
        }

        # Translate parameters using diode-specific mappings
        original_params = model_data.get('parameters', {})
        translated_params = {}

        for param_name, param_value in original_params.items():
            try:
                # Get diode-specific parameter mapping
                mapping = get_device_parameter_mapping(param_name, 'diode', Format.SPECTRE, Format.NGSPICE)
                target_name = mapping.target_name
                converted_value = self._convert_parameter_value(param_value, mapping)
                translated_params[target_name] = converted_value
                logger.debug(f"Diode: Mapped '{param_name}' -> '{target_name}': {param_value} -> {converted_value}")
            except KeyError:
                # Keep unmapped parameters as-is with warning
                if isinstance(param_value, dict) and 'value' in param_value:
                    translated_params[param_name] = param_value['value']
                else:
                    translated_params[param_name] = param_value
                logger.warning(f"No diode mapping found for parameter '{param_name}' in model {model_name}")

        ngspice_model['parameters'] = translated_params
        logger.info(f"Translated diode model '{model_name}' to ngspice format")
        return ngspice_model

    def _translate_capacitor_model(self, model_data: Dict[str, Any]) -> Dict[str, Any]:
        """Translate capacitor model from Spectre to ngspice format.
        
        Args:
            model_data: Spectre capacitor model data
            
        Returns:
            Translated ngspice capacitor model
        """
        from .parameter_mappings import get_device_parameter_mapping
        
        model_name = model_data.get('name', 'unknown_capacitor')
        
        # Create ngspice capacitor model structure
        ngspice_model = {
            'name': model_name,
            'type': 'c',  # Capacitor type in ngspice
            'category': 'capacitor',
            'parameters': {},
            'comments': model_data.get('comments', [])
        }

        # Translate parameters using capacitor-specific mappings
        original_params = model_data.get('parameters', {})
        translated_params = {}

        for param_name, param_value in original_params.items():
            try:
                # Get capacitor-specific parameter mapping
                mapping = get_device_parameter_mapping(param_name, 'capacitor', Format.SPECTRE, Format.NGSPICE)
                target_name = mapping.target_name
                converted_value = self._convert_parameter_value(param_value, mapping)
                translated_params[target_name] = converted_value
                logger.debug(f"Capacitor: Mapped '{param_name}' -> '{target_name}': {param_value} -> {converted_value}")
            except KeyError:
                # Keep unmapped parameters as-is with warning
                if isinstance(param_value, dict) and 'value' in param_value:
                    translated_params[param_name] = param_value['value']
                else:
                    translated_params[param_name] = param_value
                logger.warning(f"No mapping found for Spectre parameter '{param_name}' in model {model_name}")

        ngspice_model['parameters'] = translated_params
        logger.info(f"Translated Spectre capacitor model '{model_name}' to ngspice format")
        return ngspice_model

    def _translate_mosfet_model(self, model_data: Dict[str, Any]) -> Dict[str, Any]:
        """Translate MOSFET model from Spectre to ngspice format (original logic).
        
        Args:
            model_data: Spectre MOSFET model data
            
        Returns:
            Translated ngspice MOSFET model
        """
        # Extract model information
        model_name = model_data.get('name', 'unknown_model')
        model_type = model_data.get('type', 'nmos')
        model_category = model_data.get('category', 'unknown')

        # Skip subckt models - only translate BSIM4 models
        # Check multiple indicators for subckt models
        is_subckt = (
            model_category in ['subckt', 'subcircuit'] or
            'subckt' in model_type.lower() or
            model_type in ['nch', 'pch'] and 'multi' in str(model_data.get('parameters', {}))
        )

        if is_subckt:
            logger.debug(f"Skipping subckt model '{model_name}' - subcircuits are not translated (use core BSIM4 models instead)")
            # Return a marker dict to indicate this model should be skipped gracefully
            return {
                'name': model_name,
                'skip': True,
                'reason': 'subcircuit',
                'type': model_type,
                'category': model_category
            }

        # Create ngspice model structure
        ngspice_model = {
            'name': model_name,
            'type': self._translate_model_type(model_type),
            'category': model_category,
            'level': model_data.get('level'),  # Preserve original level for mapping
            'parameters': {},
            'comments': model_data.get('comments', [])
        }

        # Translate parameters
        original_params = model_data.get('parameters', {})
        translated_params = {}

        for param_name, param_value in original_params.items():
            # Use intelligent parameter mapping
            intelligent_mapping = self._find_intelligent_parameter_mapping(param_name, Format.NGSPICE)

            if intelligent_mapping:
                target_name = intelligent_mapping.target_name
                # Convert parameter value if needed
                converted_value = self._convert_parameter_value(param_value, intelligent_mapping)
                translated_params[target_name] = converted_value
                logger.debug(f"Intelligently mapped Spectre parameter '{param_name}' -> ngspice parameter '{target_name}': {param_value} -> {converted_value} (confidence: {intelligent_mapping.confidence})")
            else:
                # Fallback: Check if parameter needs mapping using old method
                if param_name in self.parameter_mappings:
                    mapping = self.parameter_mappings[param_name]
                    target_name = mapping.target_name
                    # Convert parameter value if needed
                    converted_value = self._convert_parameter_value(param_value, mapping)
                    translated_params[target_name] = converted_value
                    logger.debug(f"Mapped Spectre parameter '{param_name}' -> ngspice parameter '{target_name}': {param_value} -> {converted_value}")
                else:
                    # Keep parameter as-is if no mapping found, but extract value if it's a dict
                    if isinstance(param_value, dict) and 'value' in param_value:
                        translated_params[param_name] = param_value['value']
                    else:
                        translated_params[param_name] = param_value
                    logger.warning(f"No mapping found for Spectre parameter '{param_name}' in model {model_name}")

        ngspice_model['parameters'] = translated_params

        # Validate and correct BSIM4 parameters for simulation stability
        ngspice_model['parameters'] = self.validate_and_correct_parameters(ngspice_model['parameters'])

        # Validate translated model
        self._validate_model(ngspice_model)

        logger.info(f"Translated Spectre MOSFET model '{model_name}' to ngspice format")
        return ngspice_model

    def _translate_single_model(self, model_data: Dict[str, Any]) -> Tuple[Dict[str, Any], int, int, float]:
        """Override to use device-specific parameter mappings for statistics.

        Args:
            model_data: Source model data

        Returns:
            Tuple of (translated_model, mapped_count, unmapped_count, confidence_score)
        """
        from .parameter_mappings import get_device_parameter_mapping, detect_device_type_from_model
        
        translated_model = self.translate_model(model_data)
        source_params = model_data.get('parameters', {})
        target_params = translated_model.get('parameters', {})

        # Detect device type for appropriate parameter mappings
        device_type = detect_device_type_from_model(model_data)
        
        mapped_count = 0
        unmapped_count = 0
        total_confidence_weight = 0.0
        weighted_confidence_sum = 0.0

        # Analyze parameter mappings using device-specific mappings
        for param_name, param_value in source_params.items():
            weight = 1.0  # Standard weight for all parameters
            
            try:
                # Try to get device-specific mapping
                mapping = get_device_parameter_mapping(param_name, device_type, self.source_format, self.target_format)
                confidence_value = self._confidence_to_numeric(mapping.confidence)
                weighted_confidence_sum += confidence_value * weight
                total_confidence_weight += weight
                mapped_count += 1
            except KeyError:
                # Parameter not mapped
                unmapped_count += 1
                # Use penalty for unmapped parameters
                penalty = 0.5  # Neutral penalty
                weighted_confidence_sum += penalty * weight
                total_confidence_weight += weight

        # Calculate weighted average confidence
        if total_confidence_weight > 0:
            avg_confidence = weighted_confidence_sum / total_confidence_weight
        else:
            avg_confidence = 0.0

        return translated_model, mapped_count, unmapped_count, avg_confidence

    def _determine_emitted_model_type(self, model_data: Dict[str, Any]) -> str:
        """Determine the emitted model type for ngspice based on device detection."""
        from .parameter_mappings import detect_device_type_from_model
        
        device_type = detect_device_type_from_model(model_data)
        
        if device_type.lower() in ['bjt', 'npn', 'pnp']:
            bjt_type = self._determine_bjt_type(model_data)
            return bjt_type  # Return 'npn' or 'pnp'
        elif device_type.lower() in ['diode', 'dio', 'd']:
            return 'd'
        elif device_type.lower() in ['capacitor', 'cap', 'c']:
            return 'c'  # Capacitor model type for ngspice
        else:
            # MOSFET behavior - use bsim4 for modern BSIM models
            return 'bsim4'

    def _determine_bjt_type(self, model_data: Dict[str, Any]) -> str:
        """Determine BJT type (NPN or PNP) from model data.
        
        Args:
            model_data: Model data dictionary
            
        Returns:
            BJT type string ('npn' or 'pnp')
        """
        model_name = model_data.get('name', '').lower()
        model_type = model_data.get('type', '').lower()
        
        # Check model name for type hints (most reliable for Spectre models)
        if 'pnp' in model_name or 'vpnp' in model_name:
            return 'pnp'
        elif 'npn' in model_name or 'vnpn' in model_name:
            return 'npn'
        
        # Check explicit type specification
        if 'pnp' in model_type:
            return 'pnp'
        elif 'npn' in model_type:
            return 'npn'
        
        # Check parameters for type hints
        params = model_data.get('parameters', {})
        
        # Look for type parameter
        if 'type' in params:
            type_val = params['type']
            if isinstance(type_val, dict) and 'value' in type_val:
                type_val = type_val['value']
            if str(type_val) == '0':
                return 'npn'  # type=0 typically means NPN
            elif str(type_val) == '1':
                return 'pnp'  # type=1 typically means PNP
        
        # Default to NPN if can't determine
        return 'npn'

    def _translate_model_type(self, spectre_type: str) -> str:
        """Translate Spectre model type to ngspice model type.

        Args:
            spectre_type: Spectre model type

        Returns:
            ngspice model type
        """
        # Handle BSIM model types based on level
        if spectre_type.lower() == 'bsim3v3':
            # BSIM3v3 in Spectre typically corresponds to BSIM4 in ngspice
            # The level parameter will be set separately
            return 'bsim4'
        elif spectre_type.lower() == 'bsim4':
            return 'bsim4'

        # Device type mapping
        type_mapping = {
            'bjt': 'npn',      # Default to npn, actual type determined by _determine_bjt_type
            'diode': 'd',      # Diode type
            'capacitor': 'c',  # Capacitor
            'resistor': 'r',   # Resistor
            'inductor': 'l',   # Inductor
            'nmos': 'nmos',    # NMOS
            'pmos': 'pmos',    # PMOS
        }

        # Check if it's a direct mapping
        if spectre_type.lower() in type_mapping:
            return type_mapping[spectre_type.lower()]

        # For MOSFET types, return as lowercase
        if spectre_type.lower() in ['nmos', 'pmos']:
            return spectre_type.lower()

        # Default to BSIM4 for unknown MOSFET-like types
        return 'bsim4'

        return type_mapping.get(spectre_type.lower(), spectre_type.lower())

    def _convert_parameter_value(self, value: Any, mapping: Any) -> Any:
        """Convert parameter value based on mapping rules.

        Args:
            value: Original parameter value
            mapping: Parameter mapping information

        Returns:
            Converted parameter value
        """
        # Extract value if it's a dict with 'value' key
        if isinstance(value, dict) and 'value' in value:
            return value['value']
        # For now, return value as-is. Could add unit conversions, etc.
        return value

    def _validate_model(self, model_data: Dict[str, Any]) -> None:
        """Validate translated ngspice model.

        Args:
            model_data: Model data to validate

        Raises:
            TranslationError: If validation fails
        """
        required_fields = ['name', 'type', 'parameters']
        for field in required_fields:
            if field not in model_data:
                raise TranslationError(f"Translated model missing required field: {field}")

        if not isinstance(model_data.get('parameters', {}), dict):
            raise TranslationError("Model parameters must be a dictionary")

    def generate_output(self, models: List[Dict[str, Any]],
                       output_path: str,
                       include_comments: bool = True) -> str:
        """Generate ngspice .lib format output from translated models.

        Args:
            models: List of translated model dictionaries
            output_path: Path for output file
            include_comments: Whether to include comments

        Returns:
            Generated output content
        """
        try:
            lines = []

            # Add header comment
            if include_comments:
                lines.append(f"* ngspice model library generated from Spectre")
                lines.append(f"* Source: Spectre models")
                lines.append(f"* Generated for: {output_path}")
                lines.append("")

            # Generate model statements
            for model_data in models:
                model_name = model_data['name']
                raw_model_type = model_data.get('type', '')
                parameters = model_data.get('parameters', {})

                # Determine final model type to emit. Some PDKs or earlier stages may
                # leave stray tokens like 'diode' or omit the explicit type; for
                # models that are BSIM4-like (often model names end with '_bsim4' or
                # the translated type is 'bsim4') we must ensure the emitted type is
                # the explicit token 'bsim4' so ngspice parses it as a transistor
                # model rather than a diode or other device.
                model_type = self._determine_emitted_model_type(model_name, raw_model_type, model_data.get('level'))

                # Build parameter string
                param_parts = []
                for param_name, param_value in parameters.items():
                    if param_value is not None:
                        # ensure we don't accidentally emit tokens that look like
                        # model-type keywords as standalone parameters
                        if isinstance(param_value, str) and param_value.strip().lower() in ('diode', 'd', 'bjt'):
                            # move such suspicious values into a comment form instead
                            logger.debug(f"Stripping suspicious parameter value for '{param_name}' in model '{model_name}': {param_value}")
                            continue
                        param_parts.append(f"{param_name}={param_value}")

                # Create model line. Use parentheses for parameter list when present.
                if param_parts:
                    param_str = " ".join(param_parts)
                    model_line = f".model {model_name} {model_type} ({param_str})"
                else:
                    model_line = f".model {model_name} {model_type}"

                lines.append(model_line)

                # Add comments if available
                if include_comments and model_data.get('comments'):
                    for comment in model_data['comments']:
                        lines.append(f"* {comment}")

            lines.append("")  # Final newline

            output_content = "\n".join(lines)
            logger.info(f"Generated ngspice output for {len(models)} models")
            return output_content

        except Exception as e:
            error_msg = f"Failed to generate ngspice output: {str(e)}"
            logger.error(error_msg)
            raise TranslationError(error_msg) from e

    def generate_syntax(self, translated_model: Dict[str, Any]) -> str:
        """Generate ngspice syntax from translated model data.

        Args:
            translated_model: Translated model data

        Returns:
            ngspice format syntax string
        """
        lines = []

        # Add header comment
        lines.append(f"* Translated from Spectre to ngspice")
        lines.append(f"* Original model: {translated_model.get('metadata', {}).get('source_model', 'unknown')}")
        lines.append("")

        # Generate model statement
        model_name = translated_model['name']
        model_type = translated_model['type']

        # Determine ngspice level - map Spectre levels to ngspice levels
        original_level = translated_model.get('level')
        model_type = translated_model.get('type', '').lower()
        
        # Set appropriate level based on device type
        if model_type in ('pnp', 'npn'):
            # BJT models use level 1
            ngspice_level = 1
        elif model_type == 'd':
            # Diode models use level 1
            ngspice_level = 1
        elif model_type == 'c':
            # Capacitor models don't use levels in ngspice
            ngspice_level = None
        else:
            # MOSFET/BSIM4 models: Spectre BSIM4 typically uses level=54, which maps to ngspice level=14
            ngspice_level = 14 if original_level == 54 else (original_level or 14)

        # For ngspice compatibility, ensure model names don't conflict with parameter names
        # Only add _bsim4 suffix for MOSFET models
        safe_model_names = {
            'nch': 'nmos_bsim4',
            'pch': 'pmos_bsim4',
            'nch_hvt': 'nmos_hvt_bsim4',
            'pch_hvt': 'pmos_hvt_bsim4',
            'nch_lvt': 'nmos_lvt_bsim4',
            'pch_lvt': 'pmos_lvt_bsim4',
        }
        
        if model_name in safe_model_names:
            ngspice_model_name = safe_model_names[model_name]
        elif model_type in ('pnp', 'npn', 'd', 'c'):
            # Don't add _bsim4 suffix to BJT, diode, and capacitor models
            ngspice_model_name = model_name
        elif not model_name.endswith('_bsim4'):
            ngspice_model_name = f"{model_name}_bsim4"
        else:
            ngspice_model_name = model_name

        # Build parameter string for ngspice format
        parameters = translated_model.get('parameters', {})
        # Determine emitted model type using proper device detection
        model_type = self._determine_emitted_model_type(translated_model)

        if parameters:
            param_parts = []
            for param_name, param_value in parameters.items():
                if param_value is not None:
                    # Extract value if it's still a dict (fallback handling)
                    if isinstance(param_value, dict) and 'value' in param_value:
                        param_value = param_value['value']
                    param_parts.append(f"{param_name}={param_value}")
            if param_parts:
                param_str = " ".join(param_parts)
                if ngspice_level is not None:
                    model_line = f".model {ngspice_model_name} {model_type} level={ngspice_level} ({param_str})"
                else:
                    model_line = f".model {ngspice_model_name} {model_type} ({param_str})"
            else:
                if ngspice_level is not None:
                    model_line = f".model {ngspice_model_name} {model_type} level={ngspice_level}"
                else:
                    model_line = f".model {ngspice_model_name} {model_type}"
        else:
            if ngspice_level is not None:
                model_line = f".model {ngspice_model_name} {model_type} level={ngspice_level}"
            else:
                model_line = f".model {ngspice_model_name} {model_type}"

        lines.append(model_line)
        lines.append("")

        return "\n".join(lines)
