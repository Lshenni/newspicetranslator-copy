#!/usr/bin/env python3
"""
HSPICE to ngspice translator implementation.

This module provides translation from HSPICE (.inc/.sp) format to ngspice (.lib) format.
"""

from typing import Dict, Any, List
import logging
from .base_translator import BaseTranslator, Format, TranslationError
from .parameter_mappings import get_all_mappings_for_formats

logger = logging.getLogger(__name__)


class HSPICEToNgspiceTranslator(BaseTranslator):
    """Translator for converting HSPICE models to ngspice format."""

    def __init__(self) -> None:
        """Initialize HSPICE to ngspice translator."""
        super().__init__(Format.HSPICE, Format.NGSPICE)

    def _load_parameter_mappings(self) -> None:
        """Load parameter mappings for HSPICE to ngspice translation."""
        self.parameter_mappings = get_all_mappings_for_formats(
            Format.HSPICE, Format.NGSPICE
        )
        logger.info(f"Loaded {len(self.parameter_mappings)} parameter mappings for HSPICE->ngspice")

    def translate_model(self, model_data: Dict[str, Any]) -> Dict[str, Any]:
        """Translate a single HSPICE model to ngspice format.

        Args:
            model_data: Parsed HSPICE model data

        Returns:
            Translated model data in ngspice format

        Raises:
            TranslationError: If translation fails
        """
        try:
            # Extract model information
            model_name = model_data.get('name', 'unknown_model')
            model_type = model_data.get('type', 'nmos')

            # Create ngspice model structure
            ngspice_model = {
                'name': model_name,
                'type': self._translate_model_type(model_type),
                'category': model_data.get('category', 'unknown'),
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
                    logger.debug(f"Intelligently mapped HSPICE parameter '{param_name}' -> ngspice parameter '{target_name}': {param_value} -> {converted_value} (confidence: {intelligent_mapping.confidence})")
                else:
                    # Fallback: Check if parameter needs mapping using old method
                    if param_name in self.parameter_mappings:
                        mapping = self.parameter_mappings[param_name]
                        target_name = mapping.target_name
                        # Convert parameter value if needed
                        converted_value = self._convert_parameter_value(param_value, mapping)
                        translated_params[target_name] = converted_value
                        logger.debug(f"Mapped HSPICE parameter '{param_name}' -> ngspice parameter '{target_name}': {param_value} -> {converted_value}")
                    else:
                        # Keep parameter as-is if no mapping found, but extract value if it's a dict
                        if isinstance(param_value, dict) and 'value' in param_value:
                            translated_params[param_name] = param_value['value']
                        else:
                            translated_params[param_name] = param_value
                        logger.warning(f"No mapping found for HSPICE parameter '{param_name}' in model {model_name}")

            ngspice_model['parameters'] = translated_params

            # Validate and correct BSIM4 parameters for simulation stability
            ngspice_model['parameters'] = self.validate_and_correct_parameters(ngspice_model['parameters'])

            # Validate translated model
            self._validate_model(ngspice_model)

            logger.info(f"Translated HSPICE model '{model_name}' to ngspice format")
            return ngspice_model

        except Exception as e:
            error_msg = f"Failed to translate HSPICE model '{model_data.get('name', 'unknown')}' to ngspice: {str(e)}"
            logger.error(error_msg)
            raise TranslationError(error_msg) from e

    def _translate_model_type(self, hspice_type: str) -> str:
        """Translate HSPICE model type to ngspice model type.

        Args:
            hspice_type: HSPICE model type

        Returns:
            ngspice model type
        """
        # HSPICE and ngspice use similar model type names, but ensure lowercase
        type_mapping = {
            'NMOS': 'nmos',
            'PMOS': 'pmos',
            'BJT': 'npn',  # Default to npn, could be more sophisticated
            'DIODE': 'd',
            'CAPACITOR': 'c',
            'RESISTOR': 'r'
        }

        return type_mapping.get(hspice_type.upper(), hspice_type.lower())

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
                lines.append(f"* ngspice model library generated from HSPICE")
                lines.append(f"* Source: HSPICE models")
                lines.append(f"* Generated for: {output_path}")
                lines.append("")

            # Generate model statements
            for model_data in models:
                model_name = model_data['name']
                model_type = model_data['type']
                parameters = model_data['parameters']

                # Build parameter string
                param_parts = []
                for param_name, param_value in parameters.items():
                    if param_value is not None:
                        param_parts.append(f"{param_name}={param_value}")

                # Create model line
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
        lines.append(f"* Translated from HSPICE to ngspice")
        lines.append(f"* Original model: {translated_model.get('metadata', {}).get('source_model', 'unknown')}")
        lines.append("")

        # Generate model statement
        model_name = translated_model['name']
        model_type = translated_model['type']

        # Determine ngspice level - use base class mapping for compatibility
        original_level = translated_model.get('level', 54)
        ngspice_level = self._map_model_level(original_level)

        # Build parameter string for ngspice format
        parameters = translated_model.get('parameters', {})
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
                model_line = f".model {model_name} {model_type} level={ngspice_level} ({param_str})"
            else:
                model_line = f".model {model_name} {model_type} level={ngspice_level}"
        else:
            model_line = f".model {model_name} {model_type} level={ngspice_level}"

        lines.append(model_line)
        lines.append("")

        return "\n".join(lines)
