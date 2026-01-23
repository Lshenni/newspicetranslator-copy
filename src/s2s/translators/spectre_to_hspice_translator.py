"""
Spectre to HSPICE translator implementation.

This module provides translation from Spectre (.scs) format to HSPICE (.sp) format.
"""

from typing import Dict, Any, List
import logging
from .base_translator import BaseTranslator, Format, TranslationError
from .parameter_mappings import get_all_mappings_for_formats

logger = logging.getLogger(__name__)


class SpectreToHSPICETranslator(BaseTranslator):
    """Translator for converting Spectre models to HSPICE format."""

    def __init__(self) -> None:
        """Initialize Spectre to HSPICE translator."""
        super().__init__(Format.SPECTRE, Format.HSPICE)

    def _load_parameter_mappings(self) -> None:
        """Load parameter mappings for Spectre to HSPICE translation."""
        self.parameter_mappings = get_all_mappings_for_formats(
            Format.SPECTRE, Format.HSPICE
        )
        logger.info(f"Loaded {len(self.parameter_mappings)} parameter mappings for Spectre->HSPICE")

    def translate_model(self, model_data: Dict[str, Any]) -> Dict[str, Any]:
        """Translate a single Spectre model to HSPICE format.

        Args:
            model_data: Parsed Spectre model data

        Returns:
            Translated model data in HSPICE format

        Raises:
            TranslationError: If translation fails
        """
        try:
            # Extract model information
            model_name = model_data.get('name', 'unknown_model')
            model_type = model_data.get('type', 'nmos')
            level = model_data.get('level')

            # Create HSPICE model structure
            hspice_model = {
                'name': model_name,
                'type': self._translate_model_type(model_type),
                'category': model_data.get('category', 'unknown'),
                'pdk_name': model_data.get('pdk_name', 'unknown'),
                'corner': model_data.get('corner', 'tt'),
                'parameters': {},
                'metadata': {
                    'source_format': 'spectre',
                    'target_format': 'hspice',
                    'original_level': level,
                    'translated_at': 'current_timestamp'  # Would use actual timestamp
                }
            }

            # Add level if specified
            if level:
                hspice_model['level'] = level

            # Translate parameters
            source_params = model_data.get('parameters', {})
            translated_params = {}

            for param_name, param_value in source_params.items():
                if param_name in self.parameter_mappings:
                    mapping = self.parameter_mappings[param_name]
                    translated_name = mapping.target_name

                    # Apply transformation if specified
                    if mapping.transformation:
                        param_value = self._apply_transformation(param_value, mapping.transformation)

                    # Apply unit conversion if specified
                    if mapping.unit_conversion:
                        param_value = self._apply_unit_conversion(param_value, mapping.unit_conversion)

                    translated_params[translated_name] = param_value
                else:
                    # Try to discover mapping for unseen parameter
                    mapped_name, mapped_value = self.handle_unseen_parameter(param_name, param_value)

                    if mapped_name:
                        translated_params[mapped_name] = mapped_value
                        logger.info(f"Discovered mapping for Spectre parameter '{param_name}' -> '{mapped_name}' in model {model_name}")
                    else:
                        # Keep unmapped parameters with a warning
                        translated_params[param_name] = param_value
                        logger.warning(f"No mapping found for Spectre parameter '{param_name}' in model {model_name}")

            hspice_model['parameters'] = translated_params

            return hspice_model

        except Exception as e:
            raise TranslationError(f"Failed to translate Spectre model to HSPICE: {e}") from e

    def generate_syntax(self, translated_model: Dict[str, Any]) -> str:
        """Generate HSPICE syntax from translated model data.

        Args:
            translated_model: Translated model data

        Returns:
            HSPICE format syntax string
        """
        lines = []

        # Add header comment
        lines.append("* Translated from Spectre to HSPICE")
        lines.append(f"* Original model: {translated_model.get('metadata', {}).get('source_model', 'unknown')}")
        lines.append("")

        # Generate model statement
        model_name = translated_model['name']
        model_type = translated_model['type']
        level = translated_model.get('level', 54)

        model_line = f".model {model_name} {model_type} level={level}"
        lines.append(model_line)

        # Generate parameters
        parameters = translated_model.get('parameters', {})
        if parameters:
            param_lines = []
            for param_name, param_value in parameters.items():
                if isinstance(param_value, dict) and 'value' in param_value:
                    # Handle structured parameter values
                    value = param_value['value']
                    unit = param_value.get('unit', '')
                    param_lines.append(f"+{param_name} = {value}{unit}")
                else:
                    # Handle simple parameter values
                    param_lines.append(f"+{param_name} = {param_value}")

            # Join parameters with continuation lines
            if len(param_lines) > 0:
                lines.extend(param_lines)

        return "\n".join(lines)

    def _translate_model_type(self, spectre_type: str) -> str:
        """Translate Spectre model type to HSPICE model type.

        Args:
            spectre_type: Spectre model type

        Returns:
            HSPICE model type
        """
        # Spectre and HSPICE use similar model type names for MOSFETs
        type_mapping = {
            'nmos': 'nmos',
            'pmos': 'pmos',
            'NMOS': 'nmos',  # Handle case variations
            'PMOS': 'pmos'
        }

        return type_mapping.get(spectre_type.lower().strip(), spectre_type.lower().strip())
