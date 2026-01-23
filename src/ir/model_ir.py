"""
Intermediate Representation for SPICE models.

This module defines the core IR data structures used throughout the
translation pipeline. All parsers convert to IR, all writers read from IR.

Compliance: CONSTRAINTS.md
- Complete implementation (no TODOs)
- Full type annotations
- Google-style docstrings
- <1000 lines per file
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)


class Corner(Enum):
    """
    Process corner variations for SPICE models.
    
    Process corners represent manufacturing variations that affect
    device performance.
    """
    TT = "typical-typical"  # Typical NMOS, Typical PMOS
    FF = "fast-fast"        # Fast NMOS, Fast PMOS
    SS = "slow-slow"        # Slow NMOS, Slow PMOS
    FS = "fast-slow"        # Fast NMOS, Slow PMOS
    SF = "slow-fast"        # Slow NMOS, Fast PMOS
    
    @classmethod
    def from_string(cls, value: str) -> 'Corner':
        """
        Convert string to Corner enum.
        
        Args:
            value: String representation (e.g., 'tt', 'TT', 'typical-typical')
            
        Returns:
            Corner enum value
            
        Raises:
            ValueError: If value is not a valid corner
        """
        value_lower = value.lower()
        mapping = {
            'tt': cls.TT, 'typical-typical': cls.TT, 'typical': cls.TT,
            'ff': cls.FF, 'fast-fast': cls.FF, 'fast': cls.FF,
            'ss': cls.SS, 'slow-slow': cls.SS, 'slow': cls.SS,
            'fs': cls.FS, 'fast-slow': cls.FS,
            'sf': cls.SF, 'slow-fast': cls.SF,
        }
        if value_lower in mapping:
            return mapping[value_lower]
        raise ValueError(f"Unknown corner: {value}")


class Temperature(Enum):
    """
    Temperature conditions for SPICE simulation.
    
    Standard temperature points used in semiconductor characterization.
    """
    COLD = -40      # Cold corner (-40°C)
    NOMINAL = 25    # Room temperature (25°C)
    HOT = 125       # Hot corner (125°C)
    
    @classmethod
    def from_celsius(cls, temp: Union[int, float]) -> 'Temperature':
        """
        Convert Celsius temperature to closest standard Temperature.
        
        Args:
            temp: Temperature in Celsius
            
        Returns:
            Closest Temperature enum value
        """
        temp_values = {cls.COLD: -40, cls.NOMINAL: 25, cls.HOT: 125}
        closest = min(temp_values.items(), key=lambda x: abs(x[1] - temp))
        return closest[0]


class DeviceType(Enum):
    """Device type categories."""
    NMOS = "nmos"
    PMOS = "pmos"
    NPN = "npn"
    PNP = "pnp"
    DIODE = "diode"
    RESISTOR = "resistor"
    CAPACITOR = "capacitor"
    INDUCTOR = "inductor"
    SUBCIRCUIT = "subcircuit"
    UNKNOWN = "unknown"


@dataclass
class Condition:
    """
    Simulation condition specification.
    
    Combines process corner, temperature, and optional voltage
    to define a complete simulation condition.
    
    Attributes:
        corner: Process corner (TT, FF, SS, etc.)
        temperature: Temperature point
        voltage: Optional supply voltage (V)
    """
    corner: Corner
    temperature: Temperature
    voltage: Optional[float] = None
    
    def __str__(self) -> str:
        """
        Generate human-readable string representation.
        
        Returns:
            String like 'TT_25C' or 'FF_125C_1.8V'
        """
        parts = [
            self.corner.name,
            f"{self.temperature.value}C"
        ]
        if self.voltage is not None:
            parts.append(f"{self.voltage}V")
        return "_".join(parts)
    
    def __eq__(self, other: object) -> bool:
        """Check equality with another Condition."""
        if not isinstance(other, Condition):
            return NotImplemented
        return (
            self.corner == other.corner and
            self.temperature == other.temperature and
            self.voltage == other.voltage
        )
    
    def __hash__(self) -> int:
        """Make Condition hashable for use in sets/dicts."""
        return hash((self.corner, self.temperature, self.voltage))
    
    def to_spectre_section(self) -> str:
        """Convert to Spectre section name."""
        return self.corner.name.lower()
    
    def to_hspice_lib(self) -> str:
        """Convert to HSPICE library name."""
        temp_suffix = {
            Temperature.COLD: 'n40',
            Temperature.NOMINAL: '25',
            Temperature.HOT: '125'
        }
        return f"{self.corner.name.lower()}_{temp_suffix[self.temperature]}"
    
    def to_ngspice_lib(self) -> str:
        """Convert to ngspice library name."""
        return f"{self.corner.name.lower()}_t{self.temperature.value}"


@dataclass
class ModelVariation:
    """
    Parameter set for a specific simulation condition.
    
    Represents how model parameters change under different conditions
    (e.g., FF corner has different vth0 than TT corner).
    
    Attributes:
        condition: The simulation condition
        parameters: Parameter name -> value mapping
        source_line: Line number in source file
        source_file: Source file path
    """
    condition: Condition
    parameters: Dict[str, Any]
    source_line: int
    source_file: str
    
    def get_parameter(self, name: str, default: Any = None) -> Any:
        """
        Get parameter value with default fallback.
        
        Args:
            name: Parameter name
            default: Default value if parameter not found
            
        Returns:
            Parameter value or default
        """
        return self.parameters.get(name, default)
    
    def has_parameter(self, name: str) -> bool:
        """Check if parameter exists."""
        return name in self.parameters
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.
        
        Returns:
            Dictionary representation
        """
        return {
            'condition': {
                'corner': self.condition.corner.name,
                'temperature': self.condition.temperature.value,
                'voltage': self.condition.voltage
            },
            'parameters': self.parameters,
            'source_line': self.source_line,
            'source_file': self.source_file
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModelVariation':
        """
        Create ModelVariation from dictionary.
        
        Args:
            data: Dictionary with condition, parameters, source_line, source_file
            
        Returns:
            ModelVariation instance
        """
        condition = Condition(
            corner=Corner[data['condition']['corner']],
            temperature=Temperature(data['condition']['temperature']),
            voltage=data['condition'].get('voltage')
        )
        return cls(
            condition=condition,
            parameters=data['parameters'],
            source_line=data['source_line'],
            source_file=data['source_file']
        )


@dataclass
class SubcircuitIR:
    """
    Intermediate representation for subcircuit definitions.
    
    Represents subcircuit topology extracted from source files.
    
    Attributes:
        name: Subcircuit name
        ports: List of port names
        parameters: Default parameter values
        elements: List of element definitions
        models_used: List of model names referenced
        metadata: Additional metadata
    """
    name: str
    ports: List[str]
    parameters: Dict[str, Any] = field(default_factory=dict)
    elements: List[str] = field(default_factory=list)
    models_used: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'ports': self.ports,
            'parameters': self.parameters,
            'elements': self.elements,
            'models_used': self.models_used,
            'metadata': self.metadata
        }


@dataclass
class StatisticalBlock:
    """
    Statistical modeling information (Monte Carlo, mismatch, etc.).
    
    Attributes:
        variables: Statistical variables with distributions
        mismatch_params: Mismatch modeling parameters
        monte_carlo: Monte Carlo configuration
        metadata: Additional metadata
    """
    variables: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    mismatch_params: Dict[str, Any] = field(default_factory=dict)
    monte_carlo: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'variables': self.variables,
            'mismatch_params': self.mismatch_params,
            'monte_carlo': self.monte_carlo,
            'metadata': self.metadata
        }


@dataclass
class ModelIR:
    """
    Universal intermediate representation for SPICE models.
    
    This is the core data structure that all parsers output and all writers
    consume. It provides a format-agnostic representation of SPICE models.
    
    Attributes:
        name: Model name (e.g., 'nch', 'pch')
        model_type: Model type string (e.g., 'bsim4', 'vbic')
        device_type: Device category (NMOS, PMOS, etc.)
        base_parameters: Parameters common to all variations
        variations: Condition-specific parameter sets
        subcircuits: List of associated subcircuit definitions
        statistical: Optional statistical modeling information
        metadata: Additional metadata (version, source format, etc.)
    """
    name: str
    model_type: str
    device_type: DeviceType
    base_parameters: Dict[str, Any] = field(default_factory=dict)
    variations: List[ModelVariation] = field(default_factory=list)
    subcircuits: List[SubcircuitIR] = field(default_factory=list)
    statistical: Optional[StatisticalBlock] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_variation(
        self,
        condition: Condition,
        parameters: Dict[str, Any],
        source_line: int = 0,
        source_file: str = ""
    ) -> None:
        """
        Add a variation for a specific condition.
        
        Args:
            condition: Simulation condition
            parameters: Parameter values for this condition
            source_line: Line number in source file
            source_file: Source file path
        """
        variation = ModelVariation(
            condition=condition,
            parameters=parameters,
            source_line=source_line,
            source_file=source_file
        )
        self.variations.append(variation)
    
    def get_variation(self, condition: Condition) -> Optional[ModelVariation]:
        """
        Get variation for specific condition.
        
        Args:
            condition: Condition to search for
            
        Returns:
            ModelVariation if found, None otherwise
        """
        for var in self.variations:
            if var.condition == condition:
                return var
        return None
    
    def get_all_parameters(self, condition: Optional[Condition] = None) -> Dict[str, Any]:
        """
        Get complete parameter set for a condition.
        
        Combines base parameters with variation-specific parameters.
        Variation parameters override base parameters.
        
        Args:
            condition: Specific condition, or None for base only
            
        Returns:
            Complete parameter dictionary
        """
        params = dict(self.base_parameters)
        
        if condition is not None:
            variation = self.get_variation(condition)
            if variation:
                params.update(variation.parameters)
        
        return params
    
    def has_variations(self) -> bool:
        """Check if model has any variations."""
        return len(self.variations) > 0
    
    def get_conditions(self) -> List[Condition]:
        """
        Get list of all conditions with variations.
        
        Returns:
            List of Condition objects
        """
        return [var.condition for var in self.variations]
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.
        
        Returns:
            Dictionary representation
        """
        return {
            'name': self.name,
            'model_type': self.model_type,
            'device_type': self.device_type.value,
            'base_parameters': self.base_parameters,
            'variations': [v.to_dict() for v in self.variations],
            'subcircuits': [s.to_dict() for s in self.subcircuits],
            'statistical': self.statistical.to_dict() if self.statistical else None,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModelIR':
        """
        Create ModelIR from dictionary.
        
        Args:
            data: Dictionary representation
            
        Returns:
            ModelIR instance
        """
        subcircuits = []
        for s in data.get('subcircuits', []):
            subcircuits.append(SubcircuitIR(**s))
        
        statistical = None
        if data.get('statistical'):
            statistical = StatisticalBlock(**data['statistical'])
        
        return cls(
            name=data['name'],
            model_type=data['model_type'],
            device_type=DeviceType(data['device_type']),
            base_parameters=data.get('base_parameters', {}),
            variations=[ModelVariation.from_dict(v) for v in data.get('variations', [])],
            subcircuits=subcircuits,
            statistical=statistical,
            metadata=data.get('metadata', {})
        )
    
    def __repr__(self) -> str:
        """Developer-friendly representation."""
        var_count = len(self.variations)
        return (
            f"ModelIR(name='{self.name}', type='{self.model_type}', "
            f"device={self.device_type.value}, variations={var_count})"
        )


# Type aliases for convenience
IRModel = ModelIR
IRVariation = ModelVariation
IRCondition = Condition
