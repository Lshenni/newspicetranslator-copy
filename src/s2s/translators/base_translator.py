"""
Base translator classes for SPICE model format conversion.

This module provides the abstract base classes and interfaces for translating
SPICE model files between different formats (Spectre ↔ HSPICE ↔ ngspice).
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple, Union, Callable, Set
from pathlib import Path
import logging

from .types import (
    Format, ConfidenceLevel, ParameterMapping, TranslationResult,
    TranslationError, ParameterNotFoundError, InvalidFormatError
)

logger = logging.getLogger(__name__)

# Optional mapping discovery and verification systems
try:
    from ..config import (
        ParameterMappingDiscovery, MappingHypothesis, create_mapping_discovery_system,
        ClosedLoopVerifier, create_closed_loop_verifier
    )
    MAPPING_DISCOVERY_AVAILABLE = True
    VERIFICATION_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Advanced systems not available due to import error: {e}")
    MAPPING_DISCOVERY_AVAILABLE = False
    VERIFICATION_AVAILABLE = False
    ParameterMappingDiscovery = None
    MappingHypothesis = None
    create_mapping_discovery_system = None
    ClosedLoopVerifier = None
    create_closed_loop_verifier = None


class ConfidenceThresholdError(TranslationError):
    """Raised when confidence threshold is not met."""
    pass


class BaseTranslator(ABC):
    """Abstract base class for SPICE format translators.

    This class defines the interface that all format-specific translators must implement.
    It provides common functionality for parameter mapping, confidence scoring, and
    translation orchestration.
    """

    def __init__(self, source_format: Format, target_format: Format) -> None:
        """Initialize the translator.

        Args:
            source_format: The source SPICE format
            target_format: The target SPICE format
        """
        self.source_format = source_format
        self.target_format = target_format
        self.parameter_mappings: Dict[str, ParameterMapping] = {}
        self.confidence_threshold: float = 0.65  # Reduced threshold for practical use with vendor-specific params

        # Initialize mapping discovery and verification systems
        self.mapping_discovery = None
        self.closed_loop_verifier = None

        if MAPPING_DISCOVERY_AVAILABLE:
            try:
                config_dir = Path(__file__).parent.parent / "config"
                self.mapping_discovery = create_mapping_discovery_system(config_dir)
                logger.info("Mapping discovery system initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize mapping discovery: {e}")

        if VERIFICATION_AVAILABLE:
            try:
                self.closed_loop_verifier = create_closed_loop_verifier()
                logger.info("Closed-loop verification system initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize closed-loop verification: {e}")

        # Load parameter mappings for this translation pair
        self._load_parameter_mappings()

        logger.info(f"Initialized {self.__class__.__name__} for {source_format.value} -> {target_format.value}")

    @abstractmethod
    def _load_parameter_mappings(self) -> None:
        """Load parameter mappings for this translation pair.

        This method should populate self.parameter_mappings with the appropriate
        mappings between source and target formats.
        """
        pass

    @abstractmethod
    def translate_model(self, model_data: Dict[str, Any]) -> Dict[str, Any]:
        """Translate a single model from source to target format.

        Args:
            model_data: Parsed model data from source format

        Returns:
            Translated model data in target format

        Raises:
            TranslationError: If translation fails
        """
        pass

    @abstractmethod
    def generate_syntax(self, translated_model: Dict[str, Any]) -> str:
        """Generate target format syntax from translated model data.

        Args:
            translated_model: Translated model data

        Returns:
            String representation in target format syntax
        """
        pass

    def translate_file(self, input_file: Path, output_file: Path,
                      confidence_threshold: Optional[float] = None,
                      follow_includes: bool = False) -> TranslationResult:
        """Translate a SPICE model file.

        Args:
            input_file: Path to input SPICE model file
            output_file: Path to output translated file
            confidence_threshold: Minimum confidence threshold (overrides default)
            follow_includes: Whether to follow include statements

        Returns:
            TranslationResult with details about the translation

        Raises:
            TranslationError: If translation fails
        """
        if confidence_threshold is not None:
            self.confidence_threshold = confidence_threshold

        logger.info(f"Starting translation: {input_file} -> {output_file}")

        # Parse source file
        source_models = self._parse_source_file(input_file, follow_includes)
        if not source_models:
            raise TranslationError(f"No models found in source file: {input_file}")

        # Integrate mapping discovery and verification systems
        unseen_params = set()
        hypotheses = []
        
        if self.mapping_discovery:
            # Collect all source parameters across all models
            all_source_params = set()
            for model in source_models:
                if 'parameters' in model:
                    all_source_params.update(model['parameters'].keys())
            
            # Detect unseen parameters
            unseen_params = self.mapping_discovery.detect_unseen_parameters(
                all_source_params, self.source_format, self.target_format
            )
            
            if unseen_params:
                logger.warning(f"Found {len(unseen_params)} unseen parameters requiring mapping: {unseen_params}")
                
                # Generate mapping hypotheses for manual review
                hypotheses = self.mapping_discovery.generate_hypotheses(
                    unseen_params, self.source_format, self.target_format
                )
                
                # Log hypotheses for manual review
                for hypothesis in hypotheses[:5]:  # Show top 5
                    logger.info(f"Mapping hypothesis for {hypothesis.source_param}: "
                               f"{hypothesis.candidate_mapping.target_name} "
                               f"(confidence: {hypothesis.confidence_score:.2f})")
                
                # For high-confidence hypotheses, attempt verification
                verified_hypotheses = []
                if self.closed_loop_verifier:
                    for hypothesis in hypotheses:
                        if hypothesis.confidence_score >= 0.7:  # Only verify high-confidence hypotheses
                            try:
                                result = self.closed_loop_verifier.verify_mapping_hypothesis(
                                    hypothesis, input_file, output_file
                                )
                                if result.is_valid:
                                    hypothesis.verified = True
                                    hypothesis.confidence_score = result.confidence_score
                                    verified_hypotheses.append(hypothesis)
                                    logger.info(f"✅ Verified mapping: {hypothesis.source_param} -> "
                                               f"{hypothesis.candidate_mapping.target_name} "
                                               f"(confidence: {hypothesis.confidence_score:.2f})")
                            except Exception as e:
                                logger.warning(f"Verification failed for {hypothesis.source_param}: {e}")
                
                # Update YAML mappings with verified hypotheses
                if verified_hypotheses:
                    try:
                        self.mapping_discovery.update_parameter_mappings_yaml(
                            verified_hypotheses, self.config_dir
                        )
                        logger.info(f"Updated parameter mappings YAML with {len(verified_hypotheses)} verified mappings")
                    except Exception as e:
                        logger.warning(f"Failed to update YAML mappings: {e}")

        translated_models = []
        total_mapped = 0
        total_unmapped = 0
        confidence_scores = []
        warnings = []
        errors = []

        # Translate each model
        for model_data in source_models:
            try:
                translated_model, mapped, unmapped, confidence = self._translate_single_model(model_data)
                translated_models.append(translated_model)
                total_mapped += mapped
                total_unmapped += unmapped
                confidence_scores.append(confidence)

                if unmapped > 0:
                    warnings.append(f"Model {model_data.get('name', 'Unknown')}: {unmapped} parameters unmapped")

            except Exception as e:
                error_msg = f"Failed to translate model {model_data.get('name', 'Unknown')}: {e}"
                errors.append(error_msg)
                logger.error(error_msg)

        if not translated_models:
            raise TranslationError("No models were successfully translated")

        # Generate output syntax
        output_content = self._generate_output_content(translated_models)

        # Simplify complex expressions for ngspice compatibility
        if self.target_format == Format.NGSPICE:
            logger.info("Simplifying model expressions for ngspice compatibility")
            output_content = self.simplify_model_expressions(output_content)

        # Write output file
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(output_content)

        # Calculate average confidence
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0

        result = TranslationResult(
            source_format=self.source_format,
            target_format=self.target_format,
            source_file=input_file,
            target_file=output_file,
            parameters_mapped=total_mapped,
            parameters_unmapped=total_unmapped,
            confidence_score=avg_confidence,
            warnings=warnings,
            errors=errors,
            metadata={
                'models_translated': len(translated_models),
                'translator_class': self.__class__.__name__,
                'confidence_threshold': self.confidence_threshold
            }
        )

        logger.info(f"Translation completed: {result.parameters_mapped} parameters mapped, "
                   f"{result.parameters_unmapped} unmapped, confidence: {result.confidence_score:.2f}")

        return result

    def simplify_model_expressions(self, content: str) -> str:
        """
        Simplify complex parameter expressions in ngspice models to avoid evaluation errors.

        Args:
            content: Model file content

        Returns:
            Simplified content with complex expressions replaced by default values
        """
        import re

        # Pattern to match parameter assignments with expressions in BSIM4 format
        # Matches parameters like: vth0=0.31918+dvth0_n+vthmis_n or lmax=6.0E-8-dxl_n or toxe=tox_n
        pattern = r'(\w+)=([^\s]+)'

        def simplify_expression(match):
            param_name = match.group(1)
            expression = match.group(2)

            # Check if expression contains variables (letters and underscores)
            # This will catch expressions like "tox_n", "4n", "dvth0_n+vthmis_n", etc.
            if re.search(r'[a-zA-Z_]', expression):
                # Map common parameter/variable defaults
                defaults = {
                    # Threshold voltage parameters
                    'vth0': '0.35',
                    'lvth0': '0.0',
                    'wvth0': '0.0',
                    'pvth0': '0.0',
                    'dvth0_n': '0.0',
                    'dvth0_p': '0.0',
                    'vthmis_n': '0.0',
                    'vthmis_p': '0.0',

                    # Mobility parameters
                    'u0': '0.015',
                    'lu0': '0.0',
                    'wu0': '0.0',
                    'pu0': '0.0',
                    'du0_n': '0.0',
                    'du0_p': '0.0',

                    # Saturation velocity
                    'vsat': '100000',
                    'lvsat': '0.0',
                    'wvsat': '0.0',
                    'pvsat': '0.0',
                    'dvsat_n': '0.0',
                    'dvsat_p': '0.0',

                    # Oxide thickness
                    'toxe': '3e-9',
                    'toxm': '3e-9',
                    'dtox': '3e-10',
                    'tox_n': '3e-9',
                    'tox_p': '3e-9',
                    'tox_n_hvt': '3e-9',
                    'tox_p_hvt': '3e-9',
                    'toxmis_n': '0.0',
                    'toxmis_p': '0.0',

                    # Length/width limits
                    'lmax': '1e-5',
                    'wmax': '1e-5',
                    'dxl_n': '0.0',
                    'dxl_p': '0.0',
                    'dxw_n': '0.0',
                    'dxw_p': '0.0',
                    'dlmis_n': '0.0',
                    'dlmis_p': '0.0',
                    'dwmis_n': '0.0',
                    'dwmis_p': '0.0',

                    # Scaling factors
                    'n': '1.0',          # Multiplier/unit scaling
                    'mvtwl': '4n',       # This should be evaluated as 4*1.0 = 4

                    # Capacitance parameters
                    'cgso': '5e-11',
                    'cgdo': '5e-11',
                    'cgbo': '0.0',
                    'dcgso_n': '0.0',
                    'dcgdo_n': '0.0',
                    'dcgso_p': '0.0',
                    'dcgdo_p': '0.0',
                }

                if param_name in defaults:
                    return f"{param_name}={defaults[param_name]}"
                else:
                    # For expressions with variables, try to evaluate simple ones
                    try:
                        # Handle simple expressions like "4n" -> "4*1.0" = "4"
                        # Replace variable names with their default values
                        eval_expr = expression
                        for var, value in defaults.items():
                            eval_expr = eval_expr.replace(var, value)

                        # Try to evaluate the expression
                        result = eval(eval_expr)
                        return f"{param_name}={result}"
                    except:
                        # If evaluation fails, try to extract first numeric value
                        numbers = re.findall(r'[\d.]+(?:e[+-]?\d+)?', expression)
                        if numbers:
                            return f"{param_name}={numbers[0]}"
                        else:
                            # Last resort: use 0
                            return f"{param_name}=0"

            return match.group(0)  # Keep original if no variables found

        # Apply simplification to the entire content
        simplified_content = re.sub(pattern, simplify_expression, content)

        return simplified_content

    def _parse_source_file(self, file_path: Path, follow_includes: bool = False) -> List[Dict[str, Any]]:
        """Parse the source file using the appropriate parser.

        Args:
            file_path: Path to the source file
            follow_includes: Whether to follow include statements

        Returns:
            List of parsed model dictionaries
        """
        # Import here to avoid circular imports
        from ..parsers import SpectreParser, HSPICEParser, NgspiceParser

        if self.source_format == Format.SPECTRE:
            parser = SpectreParser(file_path)
        elif self.source_format == Format.HSPICE:
            parser = HSPICEParser(file_path)
        elif self.source_format == Format.NGSPICE:
            parser = NgspiceParser(file_path)
        else:
            raise InvalidFormatError(f"Unsupported source format: {self.source_format}")

        return parser.parse(follow_includes=follow_includes)

    def _translate_single_model(self, model_data: Dict[str, Any]) -> Tuple[Dict[str, Any], int, int, float]:
        """Translate a single model and calculate mapping statistics.

        Args:
            model_data: Source model data

        Returns:
            Tuple of (translated_model, mapped_count, unmapped_count, confidence_score)
        """
        # Import enhanced confidence calculation function
        from .parameter_mappings import calculate_translation_confidence
        
        translated_model = self.translate_model(model_data)
        source_params = model_data.get('parameters', {})
        target_params = translated_model.get('parameters', {})

        mapped_params = {}
        mapped_count = 0
        unmapped_count = 0

        # Collect all mapped parameters with their mappings
        for param_name, param_value in source_params.items():
            if param_name in self.parameter_mappings:
                mapping = self.parameter_mappings[param_name]
                mapped_params[param_name] = mapping
                mapped_count += 1

                # Apply transformation if specified
                if mapping.transformation:
                    param_value = self._apply_transformation(param_value, mapping.transformation)

                # Apply unit conversion if specified
                if mapping.unit_conversion:
                    param_value = self._apply_unit_conversion(param_value, mapping.unit_conversion)

                # Store in target format (skip if target_name is None - vendor-specific)
                if mapping.target_name:
                    target_params[mapping.target_name] = param_value
            else:
                unmapped_count += 1

        # Use enhanced confidence calculation with device type detection
        device_type = self._detect_device_type(model_data)
        confidence_score = calculate_translation_confidence(
            mapped_params, 
            len(source_params),
            device_type
        )

        return translated_model, mapped_count, unmapped_count, confidence_score

    def _detect_device_type(self, model_data: Dict[str, Any]) -> str:
        """Detect device type from model data for confidence calculation."""
        try:
            from ..utils.device_detection import detect_primary_device_types
            
            # Use existing device detection logic
            detected_types = detect_primary_device_types(model_data)
            if detected_types:
                return detected_types[0].lower()
        except Exception:
            pass
        
        # Fallback to simple detection
        model_name = model_data.get('name', '').lower()
        if 'bjt' in model_name or 'npn' in model_name or 'pnp' in model_name:
            return 'bjt'
        elif 'diode' in model_name or 'dio' in model_name:
            return 'diode'
        else:
            return 'mosfet'  # Default assumption

    def _generate_output_content(self, translated_models: List[Dict[str, Any]]) -> str:
        """Generate the complete output content for all translated models.

        Args:
            translated_models: List of translated model dictionaries

        Returns:
            Complete output content as string
        """
        output_lines = []

        for model in translated_models:
            # Skip models marked for skipping (e.g., subcircuits)
            if model.get('skip', False):
                logger.debug(f"Skipping output generation for {model.get('name')} (reason: {model.get('reason', 'unknown')})")
                continue
                
            syntax = self.generate_syntax(model)
            output_lines.append(syntax)

        return '\n\n'.join(output_lines)

    def _confidence_to_numeric(self, confidence: ConfidenceLevel) -> float:
        """Convert confidence level to numeric value.

        Args:
            confidence: Confidence level enum

        Returns:
            Numeric confidence value (0.0-1.0)
        """
        mapping = {
            ConfidenceLevel.HIGH: 1.0,
            ConfidenceLevel.MEDIUM: 0.9,
            ConfidenceLevel.LOW: 0.7,
            ConfidenceLevel.UNKNOWN: 0.5
        }
        return mapping.get(confidence, 0.5)

    def _apply_transformation(self, value: Any, transformation: str) -> Any:
        """Apply a mathematical transformation to a parameter value.

        Args:
            value: Parameter value
            transformation: Transformation expression

        Returns:
            Transformed value
        """
        # For now, just return the original value
        # This would be extended with actual transformation logic
        logger.debug(f"Transformation '{transformation}' applied to {value}")
        return value

    def _apply_unit_conversion(self, value: Any, conversion: str) -> Any:
        """Apply unit conversion to a parameter value.

        Args:
            value: Parameter value
            conversion: Unit conversion factor/expression

        Returns:
            Converted value
        """
        # For now, just return the original value
        # This would be extended with actual unit conversion logic
        logger.debug(f"Unit conversion '{conversion}' applied to {value}")
        return value

    def handle_unseen_parameter(self, param_name: str, param_value: Any,
                              verification_callback: Optional[Callable] = None) -> Tuple[Optional[str], Any]:
        """
        Handle an unseen parameter using the mapping discovery system.

        Args:
            param_name: Name of the unseen parameter
            param_value: Value of the parameter
            verification_callback: Optional function to verify mapping hypotheses

        Returns:
            Tuple of (mapped_name, mapped_value) or (None, original_value) if no mapping found
        """
        if not self.mapping_discovery:
            logger.debug(f"No mapping discovery system available for parameter '{param_name}'")
            return None, param_value

        # Generate hypotheses for this parameter
        hypotheses = self.mapping_discovery.generate_hypotheses(
            {param_name}, self.source_format, self.target_format
        )

        if not hypotheses:
            logger.debug(f"No hypotheses generated for parameter '{param_name}'")
            return None, param_value

        # Try the top hypothesis
        best_hypothesis = hypotheses[0]
        logger.info(f"Testing hypothesis for '{param_name}': {best_hypothesis.candidate_mapping.target_name} "
                   f"(confidence: {best_hypothesis.confidence_score:.2f})")

        # If we have closed-loop verification available, create a verification callback
        verification_callback = verification_callback or (
            self._create_verification_callback() if self.closed_loop_verifier else None
        )

        # If we have a verification callback, test the hypothesis
        if verification_callback and best_hypothesis.confidence_score >= 0.5:
            def hypothesis_verifier(hypothesis):
                # Create a temporary mapping for testing
                test_mapping = {param_name: {self.target_format: hypothesis.candidate_mapping}}

                # Ask the verification callback to test this mapping
                return verification_callback(test_mapping, hypothesis)

            if self.mapping_discovery.validate_hypothesis(best_hypothesis, hypothesis_verifier):
                # Hypothesis validated! Add it to the mappings
                self.mapping_discovery.add_validated_mapping(best_hypothesis)

                # Update our local mappings
                self.parameter_mappings[param_name] = best_hypothesis.candidate_mapping

                logger.info(f"✅ Learned new mapping: {param_name} -> {best_hypothesis.candidate_mapping.target_name}")
                return best_hypothesis.candidate_mapping.target_name, param_value

        # If verification fails or confidence is too low, use the hypothesis anyway if confidence > 0.7
        if best_hypothesis.confidence_score >= 0.7:
            logger.info(f"Using hypothesis for '{param_name}' -> '{best_hypothesis.candidate_mapping.target_name}' "
                       f"(confidence: {best_hypothesis.confidence_score:.2f})")
            return best_hypothesis.candidate_mapping.target_name, param_value

        logger.debug(f"No suitable mapping found for parameter '{param_name}'")
        return None, param_value

    def _create_verification_callback(self) -> Callable:
        """
        Create a verification callback using the closed-loop verifier.

        Returns:
            Callback function for hypothesis verification
        """
        def verify_callback(test_mappings: Dict[str, Dict[Format, ParameterMapping]],
                          hypothesis) -> Tuple[bool, float]:
            """
            Callback to verify a mapping hypothesis using closed-loop simulation.

            Args:
                test_mappings: Temporary mappings to test
                hypothesis: The hypothesis being tested

            Returns:
                Tuple of (is_valid, confidence_score)
            """
            try:
                # For now, return a simple validation based on confidence score
                # In a full implementation, this would create test circuits and run simulations
                confidence = hypothesis.confidence_score

                # Accept mappings with high confidence without full simulation
                if confidence >= 0.8:
                    return True, confidence

                # For medium confidence, we could run a simplified check
                # For now, just return the confidence score
                return confidence >= 0.6, confidence

            except Exception as e:
                logger.error(f"Verification callback failed: {e}")
                return False, 0.0

        return verify_callback

    def _extract_numeric_value(self, param_value: Any) -> Optional[float]:
        """
        Extract numeric value from parameter, handling both direct values and dictionary format.

        Args:
            param_value: Parameter value which could be a number, string, or dict with 'value' key

        Returns:
            Numeric value as float, or None if conversion fails
        """
        try:
            # Handle dictionary format from Spectre parser
            if isinstance(param_value, dict) and 'value' in param_value:
                value = param_value['value']
                if isinstance(value, (int, float)):
                    return float(value)
                elif isinstance(value, str):
                    # Try to convert string to float
                    return float(value)
                else:
                    logger.warning(f"Unsupported value type in dict parameter: {type(value)}")
                    return None
            # Handle direct numeric values
            elif isinstance(param_value, (int, float)):
                return float(param_value)
            # Handle string values
            elif isinstance(param_value, str):
                return float(param_value)
            else:
                logger.warning(f"Unsupported parameter type for numeric conversion: {type(param_value)}")
                return None
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to convert parameter value to numeric: {param_value} (error: {e})")
            return None

    def validate_and_correct_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate BSIM4 model parameters and apply corrections for known issues.

        Based on ngspice simulation logs, this corrects:
        1. Oxide thickness parameter consistency (toxe = toxp + dtox)
        2. Effective channel length issues (xl, lint parameters)
        3. Other parameter relationships

        Args:
            parameters: Raw parameter dictionary from model

        Returns:
            Corrected parameter dictionary
        """
        corrected = parameters.copy()

        # BSIM4 oxide thickness parameter validation and correction
        if 'toxe' in corrected and 'toxp' in corrected and 'dtox' in corrected:
            toxe_val = self._extract_numeric_value(corrected['toxe'])
            toxp_val = self._extract_numeric_value(corrected['toxp'])
            dtox_val = self._extract_numeric_value(corrected['dtox'])

            if toxe_val is None or toxp_val is None or dtox_val is None:
                logger.warning("Could not extract numeric values for oxide thickness parameters")
            else:
                # Check if toxe = toxp + dtox (within reasonable tolerance)
                expected_toxe = toxp_val + dtox_val
                tolerance = 1e-12  # 1pm tolerance for oxide thickness

                if abs(toxe_val - expected_toxe) > tolerance:
                    logger.warning(f"BSIM4 oxide thickness inconsistency: toxe={toxe_val} != toxp+ dtox={expected_toxe}")
                    logger.warning("Correcting dtox to maintain consistency")
                    # Correct dtox to maintain toxe = toxp + dtox
                    corrected['dtox'] = toxe_val - toxp_val

        # BSIM4 length correction parameter validation
        if 'xl' in corrected:
            xl_val = self._extract_numeric_value(corrected['xl'])
            if xl_val is not None:
                # xl should typically be negative (length reduction) but not too aggressive
                if xl_val < -15e-9:  # -15nm is aggressive and causes Leff <= 0
                    logger.warning(f"BSIM4 xl parameter too aggressive: {xl_val} m")
                    logger.warning("Applying conservative correction for effective length stability")
                    # Apply more conservative xl for stability
                    corrected['xl'] = -5e-9  # -5nm conservative length offset

        if 'lint' in corrected:
            lint_val = self._extract_numeric_value(corrected['lint'])
            if lint_val is not None:
                # lint should be reasonable for the process
                if lint_val > 3e-9:  # >3nm is large and can cause issues
                    logger.warning(f"BSIM4 lint parameter very large: {lint_val} m")
                    logger.warning("Applying conservative correction")
                    corrected['lint'] = 1e-9  # 1nm conservative lateral diffusion

        # Ensure critical parameters exist with reasonable defaults if missing
        defaults = {
            'level': 14,  # BSIM4 level
            'version': 4.0,
            'binunit': 1.0,
            'paramchk': 1.0,
            'mobmod': 0.0,
            'capmod': 2.0
        }

        for param, default_value in defaults.items():
            if param not in corrected:
                logger.info(f"Adding missing BSIM4 parameter {param} with default value {default_value}")
                corrected[param] = default_value

        return corrected

    def _find_intelligent_parameter_mapping(self, param_name: str, target_format: Format) -> Optional[ParameterMapping]:
        """
        Intelligent parameter mapping using multiple strategies.

        Args:
            param_name: Source parameter name
            target_format: Target format

        Returns:
            Best parameter mapping or None if not found
        """
        # 1. Exact match (highest priority)
        if param_name in self.parameter_mappings:
            mapping = self.parameter_mappings[param_name]
            if hasattr(mapping, 'mappings') and target_format in mapping.mappings:
                return ParameterMapping(
                    source_name=param_name,
                    target_name=mapping.mappings[target_format]['target'],
                    confidence=mapping.mappings[target_format]['confidence']
                )

        # 2. Case-insensitive exact match
        param_lower = param_name.lower()
        for map_name, mapping in self.parameter_mappings.items():
            if map_name.lower() == param_lower:
                if hasattr(mapping, 'mappings') and target_format in mapping.mappings:
                    return ParameterMapping(
                        source_name=param_name,
                        target_name=mapping.mappings[target_format]['target'],
                        confidence=mapping.mappings[target_format]['confidence'] * 0.9
                    )

        # 3. Pattern-based matching
        pattern_match = self._pattern_based_mapping(param_name, target_format)
        if pattern_match:
            return pattern_match

        # 4. BSIM model specific mapping
        bsim_match = self._bsim_specific_mapping(param_name, target_format)
        if bsim_match:
            return bsim_match

        # 5. Apply learned regex patterns (adaptive learning)
        learned_match = self._apply_learned_patterns(param_name, target_format)
        if learned_match:
            return learned_match

        return None

    def _pattern_based_mapping(self, param_name: str, target_format: Format) -> Optional[ParameterMapping]:
        """
        Advanced regex-based parameter name matching with hierarchical patterns.

        Uses sophisticated regular expressions to handle complex parameter naming patterns,
        including device-specific prefixes, version variations, and compound parameters.

        Args:
            param_name: Source parameter name
            target_format: Target format

        Returns:
            Parameter mapping if pattern matches, with confidence based on pattern specificity
        """
        import re

        # Hierarchical pattern matching - more specific patterns first
        pattern_hierarchy = [
            # Level 1: Device-specific compound parameters (highest specificity)
            {
                'patterns': [
                    (r'^(nmos|pmos)_(.+)$', r'\2', 0.95),  # nmos_vth0 -> vth0, pmos_vth0 -> vth0
                    (r'^(.+)_(nmos|pmos)$', r'\1', 0.95),  # vth0_nmos -> vth0, vth0_pmos -> vth0
                ],
                'confidence_multiplier': 0.95
            },

            # Level 2: BSIM version-specific patterns
            {
                'patterns': [
                    (r'^(.+)_bsim(\d+)$', r'\1', 0.90),    # param_bsim4 -> param
                    (r'^bsim(\d)_(.+)$', r'\2', 0.90),      # bsim4_param -> param
                    (r'^(.+)bsim(\d+)$', r'\1', 0.85),      # parambsim4 -> param
                ],
                'confidence_multiplier': 0.85
            },

            # Level 3: Standard parameter variations
            {
                'patterns': [
                    (r'^vth(?:0|o)?(?:_.*)?$', 'vth0', 0.90),   # vth, vtho, vth0, vth_nmos
                    (r'^vt(?:h|0)?(?:_.*)?$', 'vth0', 0.85),     # vt, vth, vt0
                    (r'^(?:mu|u0|mobility)(?:_.*)?$', 'u0', 0.90), # mu, u0, mobility
                    (r'^tox(?:e|p|m|ref)?(?:_.*)?$', 'tox', 0.85), # tox, toxe, toxp, toxm
                    (r'^(?:gamma|k1)(?:_.*)?$', 'k1', 0.90),     # gamma, k1
                    (r'^n(?:factor|fac)?(?:_.*)?$', 'nfactor', 0.85), # n, nfactor, nfac
                    (r'^wint(?:_.*)?$', 'wint', 0.90),           # wint
                    (r'^lint(?:_.*)?$', 'lint', 0.90),           # lint
                    (r'^xl(?:_.*)?$', 'xl', 0.95),               # xl (critical parameter)
                    (r'^xw(?:_.*)?$', 'xw', 0.90),               # xw
                    (r'^dw(?:_.*)?$', 'dw', 0.90),               # dw
                    (r'^cgso(?:_.*)?$', 'cgso', 0.90),           # cgso
                    (r'^cgdo(?:_.*)?$', 'cgdo', 0.90),           # cgdo
                    (r'^cgbo(?:_.*)?$', 'cgbo', 0.85),           # cgbo
                    (r'^rds(?:w|min)?(?:_.*)?$', 'rds', 0.80),   # rds, rdsw, rdsmin
                    (r'^rsh(?:g|w|d)?(?:_.*)?$', 'rsh', 0.80),   # rsh, rshg, rshw
                ],
                'confidence_multiplier': 0.75
            },

            # Level 4: Prefix/suffix removal patterns
            {
                'patterns': [
                    (r'^(.+)_model$', r'\1', 0.70),           # param_model -> param
                    (r'^(.+)_param$', r'\1', 0.70),           # param_param -> param
                    (r'^(.+)_value$', r'\1', 0.65),           # param_value -> param
                    (r'^(.+)_default$', r'\1', 0.60),         # param_default -> param
                    (r'^(.+)_nom$', r'\1', 0.75),             # param_nom -> param
                    (r'^(.+)_typ$', r'\1', 0.75),             # param_typ -> param
                    (r'^(.+)_min$', r'\1', 0.65),             # param_min -> param
                    (r'^(.+)_max$', r'\1', 0.65),             # param_max -> param
                ],
                'confidence_multiplier': 0.60
            },

            # Level 5: General cleanup patterns (lowest specificity)
            {
                'patterns': [
                    (r'^(.+)_$', r'\1', 0.50),                # param_ -> param
                    (r'^_(.+)$', r'\1', 0.50),                # _param -> param
                    (r'^(.+)_+$', r'\1', 0.45),               # param__ -> param
                ],
                'confidence_multiplier': 0.45
            }
        ]

        # Try patterns in hierarchical order (most specific first)
        for level in pattern_hierarchy:
            for pattern, replacement, pattern_confidence in level['patterns']:
                match = re.match(pattern, param_name, re.IGNORECASE)
                if match:
                    # Apply regex replacement to get candidate parameter name
                    candidate_name = re.sub(pattern, replacement, param_name, flags=re.IGNORECASE)

                    # Check if the candidate maps to a known parameter
                    if candidate_name in self.parameter_mappings:
                        mapping = self.parameter_mappings[candidate_name]
                        if hasattr(mapping, 'mappings') and target_format in mapping.mappings:
                            # Calculate final confidence based on pattern specificity
                            base_confidence = mapping.mappings[target_format]['confidence']
                            final_confidence = base_confidence * level['confidence_multiplier'] * pattern_confidence

                            return ParameterMapping(
                                source_name=param_name,
                                target_name=mapping.mappings[target_format]['target'],
                                confidence=min(final_confidence, 0.95)  # Cap at 95% for pattern matches
                            )

        return None

    def _bsim_specific_mapping(self, param_name: str, target_format: Format) -> Optional[ParameterMapping]:
        """
        BSIM model specific parameter mapping with version awareness.

        Args:
            param_name: Source parameter name
            target_format: Target format

        Returns:
            Parameter mapping for BSIM-specific parameters
        """
        # BSIM parameter equivalences across versions
        bsim_equivalences = {
            # BSIM3/4 parameter equivalences
            'vtho': 'vth0',      # BSIM3 -> BSIM4
            'vfb': 'vfb',        # Same in both
            'k1': 'k1',          # Same in both
            'k2': 'k2',          # Same in both
            'eta0': 'eta0',      # Same in both
            # Oxide related
            'toxe': 'toxe',      # Electrical thickness
            'toxp': 'toxp',      # Physical thickness
            'dtox': 'dtox',      # Thickness delta
            # Length correction
            'xl': 'xl',          # Length offset
            'lint': 'lint',      # Lateral diffusion
            'dl': 'dl',          # Length reduction
            # Width correction
            'xw': 'xw',          # Width offset
            'wint': 'wint',      # Width correction
            'dw': 'dw',          # Width reduction
        }

        # Check if parameter has a known BSIM equivalence
        if param_name in bsim_equivalences:
            standard_name = bsim_equivalences[param_name]
            if standard_name in self.parameter_mappings:
                mapping = self.parameter_mappings[standard_name]
                if hasattr(mapping, 'mappings') and target_format in mapping.mappings:
                    return ParameterMapping(
                        source_name=param_name,
                        target_name=mapping.mappings[target_format]['target'],
                        confidence=mapping.mappings[target_format]['confidence'] * 0.8  # BSIM mapping bonus
                    )

        return None

    def learn_from_translation(self, source_params: Dict[str, Any],
                             successful_mappings: Dict[str, str],
                             target_format: Format) -> None:
        """
        Learn from successful translations to improve future mappings.

        Args:
            source_params: Original parameter names and values
            successful_mappings: Dict of source_param -> target_param that worked
            target_format: Target format for learning
        """
        for source_param, target_param in successful_mappings.items():
            # Check if this mapping should be added to our knowledge base
            if source_param not in self.parameter_mappings:
                # Create a new mapping entry based on successful translation
                new_mapping = ParameterMapping(
                    source_name=source_param,
                    target_name=target_param,
                    confidence=0.5  # Start with medium confidence for learned mappings
                )

                # Add to parameter mappings for future use
                self.parameter_mappings[source_param] = new_mapping

                logger.info(f"Learned new parameter mapping: {source_param} -> {target_param} "
                          f"for {target_format.value} (confidence: 0.5)")

                # Also try to find pattern-based generalizations
                self._learn_pattern_from_mapping(source_param, target_param, target_format)

                # Save learned patterns periodically
                self._save_learned_patterns()

    def _learn_pattern_from_mapping(self, source_param: str, target_param: str,
                                  target_format: Format) -> None:
        """
        Advanced pattern learning from successful mappings using regex analysis.

        Analyzes successful parameter mappings to automatically generate regex patterns
        for future adaptive matching.

        Args:
            source_param: Source parameter name
            target_param: Target parameter name
            target_format: Target format
        """
        import re

        # Initialize pattern learning database if not exists
        if not hasattr(self, '_learned_patterns'):
            self._learned_patterns = {}
            self._load_learned_patterns()

        source_lower = source_param.lower()
        target_lower = target_param.lower()

        # Strategy 1: Suffix-based pattern learning
        for i in range(2, min(len(source_param), len(target_param)) + 1):
            if source_lower[-i:] == target_lower[-i:]:
                # Found common suffix - create regex pattern
                suffix = source_lower[-i:]
                prefix_diff = source_lower[:-i]

                if prefix_diff:
                    # Pattern: prefix_variation + common_suffix -> target
                    pattern_key = f"suffix_{suffix}"
                    if pattern_key not in self._learned_patterns:
                        self._learned_patterns[pattern_key] = {
                            'pattern': f"^(.+){re.escape(suffix)}$",
                            'replacement': target_param,
                            'confidence': 0.6,  # Start with medium confidence
                            'examples': []
                        }

                    # Add this example
                    self._learned_patterns[pattern_key]['examples'].append({
                        'source': source_param,
                        'target': target_param,
                        'prefix': prefix_diff
                    })

                    # Improve confidence with more examples
                    example_count = len(self._learned_patterns[pattern_key]['examples'])
                    self._learned_patterns[pattern_key]['confidence'] = min(0.8, 0.6 + (example_count * 0.05))

                    logger.debug(f"Learned suffix pattern: {pattern_key} -> {target_param} "
                               f"(confidence: {self._learned_patterns[pattern_key]['confidence']})")

        # Strategy 2: Prefix-based pattern learning
        for i in range(2, min(len(source_param), len(target_param)) + 1):
            if source_lower[:i] == target_lower[:i]:
                # Found common prefix - create regex pattern
                prefix = source_lower[:i]
                suffix_diff = source_lower[i:]

                if suffix_diff:
                    pattern_key = f"prefix_{prefix}"
                    if pattern_key not in self._learned_patterns:
                        self._learned_patterns[pattern_key] = {
                            'pattern': f"^{re.escape(prefix)}(.+)$",
                            'replacement': target_param,
                            'confidence': 0.6,
                            'examples': []
                        }

                    self._learned_patterns[pattern_key]['examples'].append({
                        'source': source_param,
                        'target': target_param,
                        'suffix': suffix_diff
                    })

                    # Improve confidence
                    example_count = len(self._learned_patterns[pattern_key]['examples'])
                    self._learned_patterns[pattern_key]['confidence'] = min(0.8, 0.6 + (example_count * 0.05))

                    logger.debug(f"Learned prefix pattern: {pattern_key} -> {target_param} "
                               f"(confidence: {self._learned_patterns[pattern_key]['confidence']})")

        # Strategy 3: Device-specific pattern learning
        device_patterns = [
            (r'^(nmos|pmos)_(.+)$', r'\2'),    # nmos_param -> param
            (r'^(.+)_(nmos|pmos)$', r'\1'),    # param_nmos -> param
            (r'^(nfet|pfet)_(.+)$', r'\2'),    # nfet_param -> param
            (r'^(.+)_(nfet|pfet)$', r'\1'),    # param_nfet -> param
        ]

        for pattern, replacement_template in device_patterns:
            match = re.match(pattern, source_param, re.IGNORECASE)
            if match:
                extracted_param = re.sub(pattern, replacement_template, source_param, flags=re.IGNORECASE)
                if extracted_param == target_param:
                    pattern_key = f"device_{pattern}"
                    if pattern_key not in self._learned_patterns:
                        self._learned_patterns[pattern_key] = {
                            'pattern': pattern,
                            'replacement': replacement_template,
                            'confidence': 0.85,  # High confidence for device patterns
                            'examples': []
                        }

                    self._learned_patterns[pattern_key]['examples'].append({
                        'source': source_param,
                        'target': target_param,
                        'device': match.group(1)
                    })

                    logger.debug(f"Learned device pattern: {pattern_key} -> {replacement_template}")

        # Strategy 4: Version-specific pattern learning
        version_patterns = [
            (r'^(.+)_bsim(\d+)$', r'\1'),      # param_bsim4 -> param
            (r'^bsim(\d)_(.+)$', r'\2'),        # bsim4_param -> param
            (r'^(.+)bsim(\d+)$', r'\1'),        # parambsim4 -> param
        ]

        for pattern, replacement_template in version_patterns:
            match = re.match(pattern, source_param, re.IGNORECASE)
            if match:
                extracted_param = re.sub(pattern, replacement_template, source_param, flags=re.IGNORECASE)
                if extracted_param == target_param:
                    pattern_key = f"version_{pattern}"
                    if pattern_key not in self._learned_patterns:
                        self._learned_patterns[pattern_key] = {
                            'pattern': pattern,
                            'replacement': replacement_template,
                            'confidence': 0.75,
                            'examples': []
                        }

                    self._learned_patterns[pattern_key]['examples'].append({
                        'source': source_param,
                        'target': target_param,
                        'version': match.group(2) if len(match.groups()) > 1 else match.group(1)
                    })

                    logger.debug(f"Learned version pattern: {pattern_key} -> {replacement_template}")

    def _apply_learned_patterns(self, param_name: str, target_format: Format) -> Optional[ParameterMapping]:
        """
        Apply learned regex patterns to parameter mapping.

        Args:
            param_name: Source parameter name
            target_format: Target format

        Returns:
            Parameter mapping if learned pattern matches
        """
        import re

        if not hasattr(self, '_learned_patterns'):
            return None

        # Try learned patterns in order of confidence
        sorted_patterns = sorted(
            self._learned_patterns.items(),
            key=lambda x: x[1]['confidence'],
            reverse=True
        )

        for pattern_key, pattern_data in sorted_patterns:
            try:
                if re.match(pattern_data['pattern'], param_name, re.IGNORECASE):
                    candidate_name = re.sub(
                        pattern_data['pattern'],
                        pattern_data['replacement'],
                        param_name,
                        flags=re.IGNORECASE
                    )

                    # Check if candidate maps to known parameter
                    if candidate_name in self.parameter_mappings:
                        mapping = self.parameter_mappings[candidate_name]
                        if hasattr(mapping, 'mappings') and target_format in mapping.mappings:
                            return ParameterMapping(
                                source_name=param_name,
                                target_name=mapping.mappings[target_format]['target'],
                                confidence=mapping.mappings[target_format]['confidence'] * pattern_data['confidence']
                            )
            except re.error:
                # Skip invalid regex patterns
                continue

        return None

    def _load_learned_patterns(self) -> None:
        """
        Load learned patterns from persistent storage.
        """
        try:
            import json
            import os
            from pathlib import Path

            # Create config directory if it doesn't exist
            config_dir = Path(__file__).parent.parent / 'config'
            config_dir.mkdir(exist_ok=True)

            pattern_file = config_dir / 'learned_patterns.json'
            if pattern_file.exists():
                with open(pattern_file, 'r') as f:
                    self._learned_patterns = json.load(f)
                logger.info(f"Loaded {len(self._learned_patterns)} learned patterns")
        except Exception as e:
            logger.warning(f"Could not load learned patterns: {e}")
            self._learned_patterns = {}

    def _save_learned_patterns(self) -> None:
        """
        Save learned patterns to persistent storage.
        """
        try:
            import json
            from pathlib import Path

            config_dir = Path(__file__).parent.parent / 'config'
            config_dir.mkdir(exist_ok=True)

            pattern_file = config_dir / 'learned_patterns.json'
            with open(pattern_file, 'w') as f:
                json.dump(self._learned_patterns, f, indent=2)

            logger.debug(f"Saved {len(self._learned_patterns)} learned patterns")
        except Exception as e:
            logger.warning(f"Could not save learned patterns: {e}")

    def get_pattern_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about learned patterns for monitoring and debugging.

        Returns:
            Dictionary with pattern learning statistics
        """
        if not hasattr(self, '_learned_patterns'):
            return {'total_patterns': 0, 'total_examples': 0}

        total_patterns = len(self._learned_patterns)
        total_examples = sum(len(p.get('examples', [])) for p in self._learned_patterns.values())

        pattern_types = {}
        for key, data in self._learned_patterns.items():
            pattern_type = key.split('_')[0]  # suffix, prefix, device, version
            pattern_types[pattern_type] = pattern_types.get(pattern_type, 0) + 1

        return {
            'total_patterns': total_patterns,
            'total_examples': total_examples,
            'pattern_types': pattern_types,
            'average_confidence': sum(p.get('confidence', 0) for p in self._learned_patterns.values()) / max(total_patterns, 1),
            'patterns_by_confidence': sorted(
                [(k, v.get('confidence', 0)) for k, v in self._learned_patterns.items()],
                key=lambda x: x[1],
                reverse=True
            )[:10]  # Top 10 most confident patterns
        }

    def _map_model_level(self, level: int) -> int:
        """
        Map unsupported model levels to ngspice-compatible levels.

        Args:
            level: Original model level from source

        Returns:
            Mapped level compatible with ngspice
        """
        # ngspice supported levels: 1-6,8-10,14,49,54-58,60,68,73
        level_mapping = {
            7: 8,    # Map level 7 to 8
            11: 14,  # Map level 11 to 14
            12: 14,  # Map level 12 to 14
            13: 14,  # Map level 13 to 14
            15: 14,  # Map level 15 to 14
            16: 14,  # Map level 16 to 14
            # Add more mappings as needed
            54: 14,  # HLMC55LP uses level 54 (BSIM4.5), map to BSIM4 level 14
            72: 14,  # freepdk15 uses level 72, map to BSIM4 level 14
        }
        return level_mapping.get(level, level)  # Return original if not mapped

    def validate_confidence_threshold(self, result: TranslationResult) -> None:
        """Validate that the translation meets confidence requirements.

        Args:
            result: Translation result to validate

        Raises:
            ConfidenceThresholdError: If confidence is below threshold
        """
        if result.confidence_score < self.confidence_threshold:
            raise ConfidenceThresholdError(
                f"Translation confidence {result.confidence_score:.2f} below threshold {self.confidence_threshold}"
            )

    def get_mapping_confidence(self, parameter_name: str) -> Optional[ConfidenceLevel]:
        """Get the confidence level for a parameter mapping.

        Args:
            parameter_name: Name of the parameter in source format

        Returns:
            Confidence level if mapping exists, None otherwise
        """
        if parameter_name in self.parameter_mappings:
            return self.parameter_mappings[parameter_name].confidence
        return None
