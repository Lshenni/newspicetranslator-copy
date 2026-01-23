"""
HSPICE to Spectre translator implementation.

This module provides translation from HSPICE (.sp) format to Spectre (.scs) format.
"""

from typing import Dict, Any, List
import logging
from .base_translator import BaseTranslator, Format, ParameterMapping, TranslationError
from .parameter_mappings import get_all_mappings_for_formats

logger = logging.getLogger(__name__)


class HSPICEToSpectreTranslator(BaseTranslator):
    """Translator for converting HSPICE models to Spectre format."""

    def __init__(self) -> None:
        """Initialize HSPICE to Spectre translator."""
        super().__init__(Format.HSPICE, Format.SPECTRE)

    def _load_parameter_mappings(self) -> None:
        """Load parameter mappings for HSPICE to Spectre translation."""
        self.parameter_mappings = get_all_mappings_for_formats(
            Format.HSPICE, Format.SPECTRE
        )
        logger.info(f"Loaded {len(self.parameter_mappings)} parameter mappings for HSPICE->Spectre")

    def translate_model(self, model_data: Dict[str, Any]) -> Dict[str, Any]:
        """Translate a single HSPICE model to Spectre format.

        Args:
            model_data: Parsed HSPICE model data

        Returns:
            Translated model data in Spectre format

        Raises:
            TranslationError: If translation fails
        """
        try:
            # Extract model information
            model_name = model_data.get('name', 'unknown_model')
            model_type = model_data.get('type', 'nmos')
            level = model_data.get('level')

            # Create Spectre model structure
            spectre_model = {
                'name': model_name,
                'type': self._translate_model_type(model_type),
                'category': model_data.get('category', 'unknown'),
                'pdk_name': model_data.get('pdk_name', 'unknown'),
                'corner': model_data.get('corner', 'tt'),
                'parameters': {},
                'metadata': {
                    'source_format': 'hspice',
                    'target_format': 'spectre',
                    'original_level': level,
                    'translated_at': 'current_timestamp'  # Would use actual timestamp
                }
            }

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
                    # Keep unmapped parameters with a warning
                    translated_params[param_name] = param_value
                    logger.warning(f"No mapping found for HSPICE parameter '{param_name}' in model {model_name}")

            spectre_model['parameters'] = translated_params

            # Add Spectre-specific metadata
            if level:
                spectre_model['level'] = self._translate_level(level)

            return spectre_model

        except Exception as e:
            raise TranslationError(f"Failed to translate HSPICE model to Spectre: {e}") from e

    def generate_syntax(self, translated_model: Dict[str, Any]) -> str:
        """Generate Spectre syntax from translated model data.

        Args:
            translated_model: Translated model data

        Returns:
            Spectre format syntax string
        """
        lines = []

        # Add header comment
        lines.append(f"// Translated from HSPICE to Spectre")
        lines.append(f"// Original model: {translated_model.get('metadata', {}).get('source_model', 'unknown')}")
        lines.append("")

        # Generate model statement
        model_name = translated_model['name']
        model_type = translated_model['type']
        level = translated_model.get('level', 54)

        model_line = f"model {model_name} {model_type} level={level} {{"
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
                    param_lines.append(f"    {param_name} = {value}{unit}")
                else:
                    # Handle simple parameter values
                    param_lines.append(f"    {param_name} = {param_value}")

            # Join parameters with continuation character
            if len(param_lines) > 0:
                lines.extend(param_lines)

        # Close model block
        lines.append("}")

        return "\n".join(lines)

    def _translate_model_type(self, hspice_type: str) -> str:
        """Translate HSPICE model type to Spectre model type.

        Args:
            hspice_type: HSPICE model type

        Returns:
            Spectre model type
        """
        # HSPICE and Spectre use similar model type names for MOSFETs
        type_mapping = {
            'nmos': 'nmos',
            'pmos': 'pmos',
            ' NMOS': 'nmos',  # Handle case variations
            ' PMOS': 'pmos'
        }

        return type_mapping.get(hspice_type.lower().strip(), hspice_type.lower().strip())

    def _translate_level(self, hspice_level: int) -> int:
        """Translate HSPICE level to Spectre level.

        Args:
            hspice_level: HSPICE level number

        Returns:
            Spectre level number
        """
        # For BSIM models, levels are typically compatible
        # Level 54 (BSIM4) maps to Spectre's BSIM4
        level_mapping = {
            54: 54,  # BSIM4
            49: 49,  # BSIM3
            14: 14,  # BSIM1 (legacy)
        }

        return level_mapping.get(hspice_level, hspice_level)
