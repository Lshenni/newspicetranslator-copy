"""
Parameter Mapper for SPICE format translation.

This module provides parameter name mapping between different SPICE formats
(Spectre, HSPICE, ngspice). It loads mappings from YAML files and provides
translation with confidence scoring.

Compliance: CONSTRAINTS.md
- Complete implementation (no TODOs)
- Full type annotations
- Google-style docstrings
- <1000 lines per file
"""

from pathlib import Path
from typing import Dict, Optional, List, Tuple, Any
import yaml
import logging
from dataclasses import dataclass
from enum import Enum


logger = logging.getLogger(__name__)


class DeviceCategory(Enum):
    """Device categories for parameter mapping."""
    MOSFET = "mosfet_bsim4"
    BJT = "bjt"
    DIODE = "diode"
    PASSIVES = "passives"


class Confidence(Enum):
    """Mapping confidence levels."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class MappingResult:
    """Result of parameter mapping operation."""
    source_param: str
    target_param: str
    confidence: Confidence
    notes: str = ""
    aliases: List[str] = None
    
    def __post_init__(self) -> None:
        """Initialize default values."""
        if self.aliases is None:
            self.aliases = []


class ParameterMapper:
    """
    Maps parameter names between SPICE formats.
    
    Loads parameter mappings from YAML files and provides translation
    between Spectre, HSPICE, and ngspice formats with confidence scoring.
    
    Attributes:
        mappings_dir: Directory containing YAML mapping files.
        _mappings: Loaded mapping data organized by device category.
        _reverse_mappings: Reverse lookup for parameter aliases.
    
    Example:
        >>> mapper = ParameterMapper()
        >>> result = mapper.map_parameter("vth0", "spectre", "ngspice", DeviceCategory.MOSFET)
        >>> print(f"{result.target_param} (confidence: {result.confidence.value})")
        vth0 (confidence: high)
    """
    
    def __init__(self, mappings_dir: Optional[Path] = None) -> None:
        """
        Initialize parameter mapper.
        
        Args:
            mappings_dir: Directory containing YAML mapping files.
                         If None, uses default mappings directory.
        """
        if mappings_dir is None:
            # Default to mappings/ subdirectory relative to this file
            self.mappings_dir = Path(__file__).parent / "mappings"
        else:
            self.mappings_dir = Path(mappings_dir)
        
        self._mappings: Dict[DeviceCategory, Dict[str, Any]] = {}
        self._reverse_mappings: Dict[DeviceCategory, Dict[str, str]] = {}
        
        # Load all mapping files
        self._load_mappings()
        logger.info(f"Loaded parameter mappings from {self.mappings_dir}")
    
    def _load_mappings(self) -> None:
        """Load all YAML mapping files from mappings directory."""
        mapping_files = {
            DeviceCategory.MOSFET: "mosfet_bsim4.yml",
            DeviceCategory.BJT: "bjt.yml",
            DeviceCategory.DIODE: "diode.yml",
            DeviceCategory.PASSIVES: "passives.yml",
        }
        
        for category, filename in mapping_files.items():
            file_path = self.mappings_dir / filename
            if not file_path.exists():
                logger.warning(f"Mapping file not found: {file_path}")
                continue
            
            try:
                with open(file_path, 'r') as f:
                    data = yaml.safe_load(f)
                    self._mappings[category] = data
                    self._build_reverse_mappings(category, data)
                    logger.debug(f"Loaded {len(data)} parameters from {filename}")
            except Exception as e:
                logger.error(f"Failed to load {file_path}: {e}")
                raise
    
    def _build_reverse_mappings(
        self, 
        category: DeviceCategory, 
        data: Dict[str, Any]
    ) -> None:
        """
        Build reverse lookup tables for parameter aliases.
        
        Args:
            category: Device category.
            data: Mapping data from YAML file.
        """
        if category not in self._reverse_mappings:
            self._reverse_mappings[category] = {}
        
        for param_name, param_data in data.items():
            # Map canonical name to itself
            self._reverse_mappings[category][param_name.lower()] = param_name
            
            # Map aliases to canonical name
            if isinstance(param_data, dict) and 'aliases' in param_data:
                for alias in param_data['aliases']:
                    self._reverse_mappings[category][alias.lower()] = param_name
    
    def map_parameter(
        self,
        param_name: str,
        source_format: str,
        target_format: str,
        category: DeviceCategory
    ) -> Optional[MappingResult]:
        """
        Map parameter name from source to target format.
        
        Args:
            param_name: Parameter name in source format.
            source_format: Source SPICE format (spectre, hspice, ngspice).
            target_format: Target SPICE format (spectre, hspice, ngspice).
            category: Device category for context.
        
        Returns:
            MappingResult with target parameter name and confidence,
            or None if no mapping found.
        
        Example:
            >>> mapper = ParameterMapper()
            >>> result = mapper.map_parameter("vth0", "spectre", "ngspice", DeviceCategory.MOSFET)
            >>> print(result.target_param)
            vth0
        """
        # Normalize inputs
        param_name = param_name.lower().strip()
        source_format = source_format.lower().strip()
        target_format = target_format.lower().strip()
        
        # Get canonical parameter name (resolve aliases)
        canonical_name = self.resolve_alias(param_name, category)
        if canonical_name is None:
            logger.debug(f"No mapping found for parameter '{param_name}' in {category.value}")
            return None
        
        # Get mapping data
        if category not in self._mappings:
            logger.warning(f"No mappings loaded for category {category.value}")
            return None
        
        param_data = self._mappings[category].get(canonical_name)
        if param_data is None:
            logger.debug(f"No mapping data for '{canonical_name}' in {category.value}")
            return None
        
        # Extract target format mapping
        target_data = param_data.get(target_format)
        if target_data is None:
            logger.debug(f"No {target_format} mapping for '{canonical_name}'")
            return None
        
        # Build result
        return MappingResult(
            source_param=param_name,
            target_param=target_data.get('target', canonical_name),
            confidence=Confidence(target_data.get('confidence', 'medium')),
            notes=target_data.get('notes', ''),
            aliases=param_data.get('aliases', [])
        )
    
    def resolve_alias(
        self, 
        param_name: str, 
        category: DeviceCategory
    ) -> Optional[str]:
        """
        Resolve parameter alias to canonical name.
        
        Args:
            param_name: Parameter name or alias.
            category: Device category.
        
        Returns:
            Canonical parameter name, or None if not found.
        
        Example:
            >>> mapper = ParameterMapper()
            >>> mapper.resolve_alias("vth", DeviceCategory.MOSFET)
            'vth0'
        """
        param_name = param_name.lower()
        
        if category not in self._reverse_mappings:
            return None
        
        return self._reverse_mappings[category].get(param_name)
    
    def map_parameters_batch(
        self,
        parameters: Dict[str, Any],
        source_format: str,
        target_format: str,
        category: DeviceCategory
    ) -> Tuple[Dict[str, Any], List[str]]:
        """
        Map multiple parameters from source to target format.
        
        Args:
            parameters: Dictionary of parameter names to values.
            source_format: Source SPICE format.
            target_format: Target SPICE format.
            category: Device category.
        
        Returns:
            Tuple of (mapped_parameters, unmapped_parameter_names).
            Mapped parameters preserve original values.
        
        Example:
            >>> mapper = ParameterMapper()
            >>> params = {"vth0": 0.4, "tox": 2.5e-9}
            >>> mapped, unmapped = mapper.map_parameters_batch(
            ...     params, "spectre", "ngspice", DeviceCategory.MOSFET
            ... )
            >>> print(mapped)
            {'vth0': 0.4, 'tox': 2.5e-9}
        """
        mapped_params: Dict[str, Any] = {}
        unmapped: List[str] = []
        
        for param_name, value in parameters.items():
            result = self.map_parameter(param_name, source_format, target_format, category)
            
            if result is not None:
                mapped_params[result.target_param] = value
                if result.confidence == Confidence.LOW:
                    logger.warning(
                        f"Low confidence mapping: {param_name} -> {result.target_param}"
                    )
            else:
                unmapped.append(param_name)
                # Keep unmapped parameters as-is (pass-through)
                mapped_params[param_name] = value
                logger.debug(f"Parameter '{param_name}' passed through unchanged")
        
        if unmapped:
            logger.info(f"Unmapped parameters ({len(unmapped)}): {', '.join(unmapped)}")
        
        return mapped_params, unmapped
    
    def get_parameter_info(
        self, 
        param_name: str, 
        category: DeviceCategory
    ) -> Optional[Dict[str, Any]]:
        """
        Get complete information about a parameter.
        
        Args:
            param_name: Parameter name to look up.
            category: Device category.
        
        Returns:
            Dictionary with parameter information including mappings
            for all formats, aliases, and notes. None if not found.
        
        Example:
            >>> mapper = ParameterMapper()
            >>> info = mapper.get_parameter_info("vth0", DeviceCategory.MOSFET)
            >>> print(info['aliases'])
            ['vth', 'vtho', 'vt0']
        """
        canonical_name = self.resolve_alias(param_name, category)
        if canonical_name is None:
            return None
        
        if category not in self._mappings:
            return None
        
        return self._mappings[category].get(canonical_name)
    
    def list_parameters(self, category: DeviceCategory) -> List[str]:
        """
        List all available parameters for a device category.
        
        Args:
            category: Device category.
        
        Returns:
            List of canonical parameter names.
        
        Example:
            >>> mapper = ParameterMapper()
            >>> params = mapper.list_parameters(DeviceCategory.MOSFET)
            >>> len(params)
            150
        """
        if category not in self._mappings:
            return []
        
        return list(self._mappings[category].keys())
    
    def validate_parameter(
        self, 
        param_name: str, 
        category: DeviceCategory
    ) -> bool:
        """
        Check if a parameter is valid for a device category.
        
        Args:
            param_name: Parameter name to validate.
            category: Device category.
        
        Returns:
            True if parameter is recognized (including aliases), False otherwise.
        
        Example:
            >>> mapper = ParameterMapper()
            >>> mapper.validate_parameter("vth0", DeviceCategory.MOSFET)
            True
            >>> mapper.validate_parameter("invalid_param", DeviceCategory.MOSFET)
            False
        """
        return self.resolve_alias(param_name, category) is not None
    
    def get_confidence_stats(
        self,
        parameters: Dict[str, Any],
        source_format: str,
        target_format: str,
        category: DeviceCategory
    ) -> Dict[str, int]:
        """
        Get confidence statistics for parameter mappings.
        
        Args:
            parameters: Dictionary of parameters to analyze.
            source_format: Source SPICE format.
            target_format: Target SPICE format.
            category: Device category.
        
        Returns:
            Dictionary with counts for high, medium, low confidence
            and unmapped parameters.
        
        Example:
            >>> mapper = ParameterMapper()
            >>> params = {"vth0": 0.4, "tox": 2.5e-9, "unknown": 1.0}
            >>> stats = mapper.get_confidence_stats(
            ...     params, "spectre", "ngspice", DeviceCategory.MOSFET
            ... )
            >>> print(stats)
            {'high': 2, 'medium': 0, 'low': 0, 'unmapped': 1}
        """
        stats = {
            'high': 0,
            'medium': 0,
            'low': 0,
            'unmapped': 0
        }
        
        for param_name in parameters:
            result = self.map_parameter(param_name, source_format, target_format, category)
            
            if result is None:
                stats['unmapped'] += 1
            else:
                stats[result.confidence.value] += 1
        
        return stats
