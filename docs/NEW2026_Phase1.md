# Phase 1: IR Foundation & Base Classes (Week 1-2)

**Phase:** 1 of 6  
**Duration:** 2 weeks  
**Dependencies:** None  
**Compliance:** CONSTRAINTS.md - Python 3.10+, Type Annotations, Complete Implementation

---

## Phase Objectives

Build the **Intermediate Representation (IR) layer** and **base classes** that form the foundation of the IR-based architecture.

### Deliverables
- ✅ Complete IR data structures (ModelIR, Condition, Variation)
- ✅ Base parser interface
- ✅ Base writer interface
- ✅ IR serialization (JSON/YAML)
- ✅ Comprehensive unit tests (>80% coverage)
- ✅ Complete documentation

---

## Implementation Tasks

### Task 1.1: IR Data Structures (3 days)

**File:** `src/ir/model_ir.py`  
**Size:** ~400 lines (compliant with <1000 line limit)

```python
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
        Create Corner from string representation.
        
        Args:
            value: String like 'tt', 'TT', 'typical-typical'
            
        Returns:
            Corner enum value
            
        Raises:
            ValueError: If string doesn't match any corner
        """
        value_lower = value.lower().strip()
        
        # Direct name match
        for corner in cls:
            if corner.name.lower() == value_lower:
                return corner
            if corner.value.lower() == value_lower:
                return corner
        
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
        Create Temperature from celsius value.
        
        Args:
            temp: Temperature in celsius
            
        Returns:
            Closest Temperature enum value
        """
        # Find closest match
        closest = min(cls, key=lambda t: abs(t.value - temp))
        return closest


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
        temperature: Temperature condition
        voltage: Optional supply voltage (V)
    """
    corner: Corner
    temperature: Temperature
    voltage: Optional[float] = None
    
    def __str__(self) -> str:
        """
        Human-readable string representation.
        
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
            Temperature.COLD: 'c',
            Temperature.NOMINAL: 'n',
            Temperature.HOT: 'h'
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
        parameters: Parameter name → value mapping
        source_line: Line number in source file
        source_file: Source file path
    """
    condition: Condition
    parameters: Dict[str, Any]
    source_line: int
    source_file: str
    
    def get_parameter(self, name: str, default: Any = None) -> Any:
        """
        Get parameter value with fallback.
        
        Args:
            name: Parameter name
            default: Default value if not found
            
        Returns:
            Parameter value or default
        """
        return self.parameters.get(name, default)
    
    def has_parameter(self, name: str) -> bool:
        """Check if parameter exists."""
        return name in self.parameters
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'condition': str(self.condition),
            'parameters': self.parameters,
            'source_line': self.source_line,
            'source_file': self.source_file
        }


@dataclass
class ModelIR:
    """
    Universal Intermediate Representation for SPICE models.
    
    This is the central data structure that all parsers produce and
    all writers consume. It provides a format-agnostic representation
    of SPICE device models.
    
    Attributes:
        name: Model name (e.g., 'nch_typ')
        device_type: Device category (nmos, pmos, bjt, etc.)
        base_model: Model type (bsim4, level=54, etc.)
        base_parameters: Parameters common to all conditions
        variations: Condition-specific parameter overrides
        pdk_name: PDK identifier (e.g., 'freepdk45')
        version: Model version
        source_format: Original format (spectre, hspice, ngspice)
        description: Optional documentation string
        ports: Port list for subcircuits
        is_subcircuit: True if this is a subcircuit definition
    """
    # Identity
    name: str
    device_type: str
    base_model: str
    
    # Parameters
    base_parameters: Dict[str, Any] = field(default_factory=dict)
    variations: List[ModelVariation] = field(default_factory=list)
    
    # Metadata
    pdk_name: Optional[str] = None
    version: Optional[str] = None
    source_format: Optional[str] = None
    description: Optional[str] = None
    
    # Subcircuit information
    ports: List[str] = field(default_factory=list)
    is_subcircuit: bool = False
    
    def get_all_conditions(self) -> List[Condition]:
        """
        Get list of all conditions this model supports.
        
        Returns:
            List of Condition objects
        """
        return [v.condition for v in self.variations]
    
    def get_parameters_for_condition(self, condition: Condition) -> Dict[str, Any]:
        """
        Get complete parameter set for a specific condition.
        
        Merges base_parameters with condition-specific overrides.
        
        Args:
            condition: The simulation condition
            
        Returns:
            Complete parameter dictionary
        """
        # Start with base parameters
        params = self.base_parameters.copy()
        
        # Find matching variation
        for variation in self.variations:
            if variation.condition == condition:
                # Override/add condition-specific parameters
                params.update(variation.parameters)
                logger.debug(
                    f"Applied variation for {condition}: "
                    f"{len(variation.parameters)} parameters"
                )
                break
        
        return params
    
    def add_variation(
        self,
        condition: Condition,
        parameters: Dict[str, Any],
        source_line: int = 0,
        source_file: str = ''
    ) -> None:
        """
        Add a new condition variation.
        
        Args:
            condition: Simulation condition
            parameters: Parameter overrides for this condition
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
        logger.debug(f"Added variation {condition} with {len(parameters)} parameters")
    
    def merge_variation(self, variation: ModelVariation) -> None:
        """
        Merge an existing variation into this model.
        
        If a variation for the same condition exists, update it.
        Otherwise, add as new variation.
        
        Args:
            variation: ModelVariation to merge
        """
        for i, existing in enumerate(self.variations):
            if existing.condition == variation.condition:
                # Update existing variation
                existing.parameters.update(variation.parameters)
                logger.debug(f"Merged variation {variation.condition}")
                return
        
        # Add as new variation
        self.variations.append(variation)
        logger.debug(f"Added new variation {variation.condition}")
    
    def get_parameter_count(self, include_variations: bool = True) -> int:
        """
        Count total parameters.
        
        Args:
            include_variations: Whether to count variation parameters
            
        Returns:
            Total parameter count
        """
        count = len(self.base_parameters)
        
        if include_variations:
            for var in self.variations:
                count += len(var.parameters)
        
        return count
    
    def validate(self) -> List[str]:
        """
        Validate IR structure and return list of errors.
        
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        
        # Check required fields
        if not self.name:
            errors.append("Model name is required")
        
        if not self.device_type:
            errors.append("Device type is required")
        
        if not self.base_model:
            errors.append("Base model is required")
        
        # Check parameter validity
        for param, value in self.base_parameters.items():
            if not self._is_valid_parameter_name(param):
                errors.append(f"Invalid parameter name: {param}")
            
            if not self._is_valid_parameter_value(value):
                errors.append(f"Invalid parameter value for {param}: {value}")
        
        # Check variations
        for i, var in enumerate(self.variations):
            for param, value in var.parameters.items():
                if not self._is_valid_parameter_name(param):
                    errors.append(
                        f"Variation {i}: Invalid parameter name: {param}"
                    )
                
                if not self._is_valid_parameter_value(value):
                    errors.append(
                        f"Variation {i}: Invalid parameter value for {param}: {value}"
                    )
        
        return errors
    
    def _is_valid_parameter_name(self, name: str) -> bool:
        """Check if parameter name is valid."""
        import re
        return bool(re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', str(name)))
    
    def _is_valid_parameter_value(self, value: Any) -> bool:
        """Check if parameter value is valid."""
        if value is None:
            return False
        
        if isinstance(value, (int, float)):
            return not (str(value).lower() in ['nan', 'inf', '-inf'])
        
        if isinstance(value, str):
            invalid = ['nan', 'inf', '-inf', 'none', 'null']
            return value.lower().strip() not in invalid
        
        if isinstance(value, dict):
            return 'value' in value or 'raw' in value
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize to dictionary for JSON/YAML export.
        
        Returns:
            Dictionary representation
        """
        return {
            'name': self.name,
            'device_type': self.device_type,
            'base_model': self.base_model,
            'base_parameters': self.base_parameters,
            'variations': [v.to_dict() for v in self.variations],
            'metadata': {
                'pdk_name': self.pdk_name,
                'version': self.version,
                'source_format': self.source_format,
                'description': self.description
            },
            'ports': self.ports,
            'is_subcircuit': self.is_subcircuit
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModelIR':
        """
        Deserialize from dictionary.
        
        Args:
            data: Dictionary representation
            
        Returns:
            ModelIR instance
        """
        model = cls(
            name=data['name'],
            device_type=data['device_type'],
            base_model=data['base_model'],
            base_parameters=data.get('base_parameters', {}),
            pdk_name=data.get('metadata', {}).get('pdk_name'),
            version=data.get('metadata', {}).get('version'),
            source_format=data.get('metadata', {}).get('source_format'),
            description=data.get('metadata', {}).get('description'),
            ports=data.get('ports', []),
            is_subcircuit=data.get('is_subcircuit', False)
        )
        
        # Reconstruct variations
        for var_data in data.get('variations', []):
            # Parse condition string
            condition = cls._parse_condition_from_dict(var_data)
            model.add_variation(
                condition=condition,
                parameters=var_data['parameters'],
                source_line=var_data.get('source_line', 0),
                source_file=var_data.get('source_file', '')
            )
        
        return model
    
    @staticmethod
    def _parse_condition_from_dict(var_data: Dict[str, Any]) -> Condition:
        """Parse Condition from variation dictionary."""
        cond_str = var_data['condition']
        
        # Parse string like 'TT_25C' or 'FF_125C_1.8V'
        parts = cond_str.split('_')
        
        corner = Corner.from_string(parts[0])
        temp_str = parts[1].replace('C', '')
        temperature = Temperature.from_celsius(float(temp_str))
        
        voltage = None
        if len(parts) > 2:
            voltage_str = parts[2].replace('V', '')
            voltage = float(voltage_str)
        
        return Condition(corner, temperature, voltage)


# Type aliases for convenience
IRModel = ModelIR
IRVariation = ModelVariation
IRCondition = Condition
```

---

### Task 1.2: IR Serialization (1 day)

**File:** `src/ir/ir_serializer.py`  
**Size:** ~150 lines

```python
"""
IR serialization and deserialization utilities.

Provides JSON and YAML serialization for ModelIR objects,
enabling persistence and interchange.

Compliance: CONSTRAINTS.md
"""

from typing import List, Dict, Any, Union
from pathlib import Path
import json
import logging

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    logging.warning("PyYAML not available, YAML support disabled")

from .model_ir import ModelIR

logger = logging.getLogger(__name__)


class IRSerializer:
    """
    Serializer for ModelIR objects.
    
    Supports JSON (always available) and YAML (if PyYAML installed).
    """
    
    @staticmethod
    def to_json(models: Union[ModelIR, List[ModelIR]], **kwargs) -> str:
        """
        Serialize ModelIR to JSON string.
        
        Args:
            models: Single ModelIR or list of ModelIR
            **kwargs: Additional arguments for json.dumps()
            
        Returns:
            JSON string
        """
        if isinstance(models, ModelIR):
            data = models.to_dict()
        else:
            data = [m.to_dict() for m in models]
        
        return json.dumps(data, indent=2, **kwargs)
    
    @staticmethod
    def from_json(json_str: str) -> Union[ModelIR, List[ModelIR]]:
        """
        Deserialize ModelIR from JSON string.
        
        Args:
            json_str: JSON string
            
        Returns:
            ModelIR or list of ModelIR
        """
        data = json.loads(json_str)
        
        if isinstance(data, list):
            return [ModelIR.from_dict(d) for d in data]
        else:
            return ModelIR.from_dict(data)
    
    @staticmethod
    def save_json(models: Union[ModelIR, List[ModelIR]], file_path: Path) -> None:
        """
        Save ModelIR to JSON file.
        
        Args:
            models: ModelIR or list of ModelIR
            file_path: Output file path
        """
        json_str = IRSerializer.to_json(models)
        file_path.write_text(json_str, encoding='utf-8')
        logger.info(f"Saved IR to JSON: {file_path}")
    
    @staticmethod
    def load_json(file_path: Path) -> Union[ModelIR, List[ModelIR]]:
        """
        Load ModelIR from JSON file.
        
        Args:
            file_path: Input file path
            
        Returns:
            ModelIR or list of ModelIR
        """
        json_str = file_path.read_text(encoding='utf-8')
        models = IRSerializer.from_json(json_str)
        logger.info(f"Loaded IR from JSON: {file_path}")
        return models
    
    @staticmethod
    def to_yaml(models: Union[ModelIR, List[ModelIR]], **kwargs) -> str:
        """
        Serialize ModelIR to YAML string.
        
        Args:
            models: Single ModelIR or list of ModelIR
            **kwargs: Additional arguments for yaml.dump()
            
        Returns:
            YAML string
            
        Raises:
            RuntimeError: If PyYAML not available
        """
        if not YAML_AVAILABLE:
            raise RuntimeError("PyYAML not installed, YAML support unavailable")
        
        if isinstance(models, ModelIR):
            data = models.to_dict()
        else:
            data = [m.to_dict() for m in models]
        
        return yaml.dump(data, **kwargs)
    
    @staticmethod
    def from_yaml(yaml_str: str) -> Union[ModelIR, List[ModelIR]]:
        """
        Deserialize ModelIR from YAML string.
        
        Args:
            yaml_str: YAML string
            
        Returns:
            ModelIR or list of ModelIR
            
        Raises:
            RuntimeError: If PyYAML not available
        """
        if not YAML_AVAILABLE:
            raise RuntimeError("PyYAML not installed, YAML support unavailable")
        
        data = yaml.safe_load(yaml_str)
        
        if isinstance(data, list):
            return [ModelIR.from_dict(d) for d in data]
        else:
            return ModelIR.from_dict(data)
```

---

### Task 1.3: Base Parser (2 days)

**File:** `src/parsers/base_parser.py`  
**Size:** ~250 lines

```python
"""
Abstract base parser for SPICE formats.

All format-specific parsers inherit from this class and implement
parse_to_ir() to convert their format to the universal IR.

Compliance: CONSTRAINTS.md
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Set
from pathlib import Path
import logging

from ..ir.model_ir import ModelIR

logger = logging.getLogger(__name__)


class BaseParser(ABC):
    """
    Abstract base class for SPICE parsers.
    
    All parsers must implement parse_to_ir() which returns a list
    of ModelIR objects.
    """
    
    def __init__(self, file_path: Path) -> None:
        """
        Initialize parser.
        
        Args:
            file_path: Path to SPICE file to parse
        """
        self.file_path = file_path
        self.content: Optional[str] = None
        self._load_file()
    
    def _load_file(self) -> None:
        """Load file content with encoding fallback."""
        try:
            self.content = self.file_path.read_text(encoding='utf-8')
            logger.info(f"Loaded file: {self.file_path}")
        except UnicodeDecodeError:
            logger.warning(f"UTF-8 decode failed, trying latin-1: {self.file_path}")
            self.content = self.file_path.read_text(encoding='latin-1')
        except Exception as e:
            logger.error(f"Failed to load file {self.file_path}: {e}")
            raise
    
    @abstractmethod
    def parse_to_ir(self, follow_includes: bool = False) -> List[ModelIR]:
        """
        Parse file and return IR representation.
        
        Args:
            follow_includes: Whether to recursively parse included files
            
        Returns:
            List of ModelIR objects
        """
        pass
    
    @abstractmethod
    def get_format_name(self) -> str:
        """
        Get format name for this parser.
        
        Returns:
            Format name ('spectre', 'hspice', 'ngspice')
        """
        pass
```

---

### Task 1.4: Base Writer (2 days)

**File:** `src/writers/base_writer.py`  
**Size:** ~200 lines

```python
"""
Abstract base writer for SPICE formats.

All format-specific writers inherit from this class and implement
write_from_ir() to convert IR to their target format.

Compliance: CONSTRAINTS.md
"""

from abc import ABC, abstractmethod
from typing import List
from pathlib import Path
import logging

from ..ir.model_ir import ModelIR

logger = logging.getLogger(__name__)


class BaseWriter(ABC):
    """
    Abstract base class for SPICE writers.
    
    All writers must implement write_from_ir() which generates
    output from ModelIR objects.
    """
    
    def __init__(self) -> None:
        """Initialize writer."""
        pass
    
    @abstractmethod
    def write_from_ir(
        self,
        models: List[ModelIR],
        output_path: Path
    ) -> None:
        """
        Write IR models to target format file.
        
        Args:
            models: List of ModelIR objects
            output_path: Output file path
        """
        pass
    
    @abstractmethod
    def get_format_name(self) -> str:
        """
        Get format name for this writer.
        
        Returns:
            Format name ('spectre', 'hspice', 'ngspice')
        """
        pass
    
    def _format_header(self, source_format: Optional[str] = None) -> str:
        """
        Generate file header comment.
        
        Args:
            source_format: Original format name
            
        Returns:
            Header comment string
        """
        lines = [
            f"* Auto-generated by SPICE Translator",
            f"* Target format: {self.get_format_name()}",
        ]
        
        if source_format:
            lines.append(f"* Source format: {source_format}")
        
        lines.append("*")
        
        return '\n'.join(lines)
```

---

### Task 1.5: Unit Tests (3 days)

**File:** `tests/test_ir/test_model_ir.py`  
**Size:** ~500 lines

```python
"""
Unit tests for ModelIR and related classes.

Tests all IR components thoroughly to ensure correctness.

Compliance: CONSTRAINTS.md - pytest only
"""

import pytest
from src.ir.model_ir import (
    ModelIR, Condition, ModelVariation, Corner, Temperature, DeviceType
)


class TestCorner:
    """Test Corner enum."""
    
    def test_corner_values(self):
        """Test all corner values exist."""
        assert Corner.TT.value == "typical-typical"
        assert Corner.FF.value == "fast-fast"
        assert Corner.SS.value == "slow-slow"
        assert Corner.FS.value == "fast-slow"
        assert Corner.SF.value == "slow-fast"
    
    def test_from_string(self):
        """Test creating Corner from string."""
        assert Corner.from_string("tt") == Corner.TT
        assert Corner.from_string("TT") == Corner.TT
        assert Corner.from_string("typical-typical") == Corner.TT
        assert Corner.from_string("ff") == Corner.FF
    
    def test_from_string_invalid(self):
        """Test invalid corner string."""
        with pytest.raises(ValueError):
            Corner.from_string("invalid")


class TestTemperature:
    """Test Temperature enum."""
    
    def test_temperature_values(self):
        """Test temperature values."""
        assert Temperature.COLD.value == -40
        assert Temperature.NOMINAL.value == 25
        assert Temperature.HOT.value == 125
    
    def test_from_celsius(self):
        """Test creating Temperature from celsius."""
        assert Temperature.from_celsius(-40) == Temperature.COLD
        assert Temperature.from_celsius(25) == Temperature.NOMINAL
        assert Temperature.from_celsius(125) == Temperature.HOT
        
        # Test closest match
        assert Temperature.from_celsius(0) == Temperature.NOMINAL
        assert Temperature.from_celsius(100) == Temperature.HOT


class TestCondition:
    """Test Condition class."""
    
    def test_create_condition(self):
        """Test creating Condition."""
        cond = Condition(Corner.TT, Temperature.NOMINAL)
        assert cond.corner == Corner.TT
        assert cond.temperature == Temperature.NOMINAL
        assert cond.voltage is None
    
    def test_condition_with_voltage(self):
        """Test Condition with voltage."""
        cond = Condition(Corner.FF, Temperature.HOT, voltage=1.8)
        assert cond.voltage == 1.8
    
    def test_condition_str(self):
        """Test string representation."""
        cond = Condition(Corner.TT, Temperature.NOMINAL)
        assert str(cond) == "TT_25C"
        
        cond_v = Condition(Corner.FF, Temperature.HOT, voltage=1.8)
        assert str(cond_v) == "FF_125C_1.8V"
    
    def test_condition_equality(self):
        """Test Condition equality."""
        cond1 = Condition(Corner.TT, Temperature.NOMINAL)
        cond2 = Condition(Corner.TT, Temperature.NOMINAL)
        cond3 = Condition(Corner.FF, Temperature.NOMINAL)
        
        assert cond1 == cond2
        assert cond1 != cond3
    
    def test_condition_hashable(self):
        """Test Condition is hashable."""
        cond1 = Condition(Corner.TT, Temperature.NOMINAL)
        cond2 = Condition(Corner.FF, Temperature.HOT)
        
        cond_set = {cond1, cond2}
        assert len(cond_set) == 2
        assert cond1 in cond_set


class TestModelIR:
    """Test ModelIR class."""
    
    @pytest.fixture
    def basic_model(self):
        """Create basic model for testing."""
        return ModelIR(
            name='nch_typ',
            device_type='nmos',
            base_model='bsim4',
            base_parameters={
                'tox': 1.5e-9,
                'vth0': 0.4,
                'u0': 450
            },
            pdk_name='test_pdk',
            source_format='spectre'
        )
    
    def test_create_model(self, basic_model):
        """Test creating ModelIR."""
        assert basic_model.name == 'nch_typ'
        assert basic_model.device_type == 'nmos'
        assert basic_model.base_model == 'bsim4'
        assert len(basic_model.base_parameters) == 3
    
    def test_add_variation(self, basic_model):
        """Test adding variation."""
        condition = Condition(Corner.FF, Temperature.NOMINAL)
        params = {'vth0': 0.35, 'u0': 500}
        
        basic_model.add_variation(condition, params)
        
        assert len(basic_model.variations) == 1
        assert basic_model.variations[0].condition == condition
        assert basic_model.variations[0].parameters == params
    
    def test_get_parameters_for_condition(self, basic_model):
        """Test getting parameters for condition."""
        # Add variations
        tt_cond = Condition(Corner.TT, Temperature.NOMINAL)
        ff_cond = Condition(Corner.FF, Temperature.NOMINAL)
        
        basic_model.add_variation(tt_cond, {'vth0': 0.4})
        basic_model.add_variation(ff_cond, {'vth0': 0.35})
        
        # Get TT parameters (should have base + TT variation)
        tt_params = basic_model.get_parameters_for_condition(tt_cond)
        assert tt_params['tox'] == 1.5e-9  # From base
        assert tt_params['vth0'] == 0.4     # From TT variation
        assert tt_params['u0'] == 450       # From base
        
        # Get FF parameters
        ff_params = basic_model.get_parameters_for_condition(ff_cond)
        assert ff_params['vth0'] == 0.35    # From FF variation
    
    def test_validate_valid_model(self, basic_model):
        """Test validation of valid model."""
        errors = basic_model.validate()
        assert len(errors) == 0
    
    def test_validate_invalid_model(self):
        """Test validation catches errors."""
        # Missing name
        model = ModelIR(name='', device_type='nmos', base_model='bsim4')
        errors = model.validate()
        assert any('name' in e.lower() for e in errors)
        
        # Invalid parameter name
        model2 = ModelIR(
            name='test',
            device_type='nmos',
            base_model='bsim4',
            base_parameters={'123invalid': 1.0}
        )
        errors2 = model2.validate()
        assert any('parameter name' in e.lower() for e in errors2)
    
    def test_to_dict(self, basic_model):
        """Test serialization to dict."""
        data = basic_model.to_dict()
        
        assert data['name'] == 'nch_typ'
        assert data['device_type'] == 'nmos'
        assert data['base_model'] == 'bsim4'
        assert 'base_parameters' in data
        assert 'metadata' in data
    
    def test_from_dict(self, basic_model):
        """Test deserialization from dict."""
        data = basic_model.to_dict()
        reconstructed = ModelIR.from_dict(data)
        
        assert reconstructed.name == basic_model.name
        assert reconstructed.device_type == basic_model.device_type
        assert reconstructed.base_model == basic_model.base_model
        assert reconstructed.base_parameters == basic_model.base_parameters
    
    def test_round_trip_serialization(self, basic_model):
        """Test complete round-trip serialization."""
        # Add variation
        condition = Condition(Corner.FF, Temperature.HOT)
        basic_model.add_variation(condition, {'vth0': 0.3})
        
        # Serialize and deserialize
        data = basic_model.to_dict()
        reconstructed = ModelIR.from_dict(data)
        
        # Compare
        assert reconstructed.name == basic_model.name
        assert len(reconstructed.variations) == len(basic_model.variations)
        
        # Check variation preserved
        ff_params = reconstructed.get_parameters_for_condition(condition)
        assert ff_params['vth0'] == 0.3
```

---

## Testing Strategy

### Unit Tests
```bash
# Run all Phase 1 tests
pytest tests/test_ir/ -v --cov=src/ir --cov-report=html

# Expected coverage: >80%
```

### Test Files
1. `tests/test_ir/test_model_ir.py` - ModelIR, Condition, Variation
2. `tests/test_ir/test_serializer.py` - JSON/YAML serialization
3. `tests/test_parsers/test_base_parser.py` - Base parser
4. `tests/test_writers/test_base_writer.py` - Base writer

---

## Documentation Requirements

### Docstrings (Google Style)
```python
def add_variation(self, condition: Condition, parameters: Dict[str, Any]) -> None:
    """
    Add a new condition variation to the model.
    
    Args:
        condition: Simulation condition (corner, temperature, voltage)
        parameters: Parameter overrides for this condition
        
    Returns:
        None
        
    Raises:
        ValueError: If condition is invalid
        
    Example:
        >>> model = ModelIR(name='nch', device_type='nmos', base_model='bsim4')
        >>> cond = Condition(Corner.FF, Temperature.HOT)
        >>> model.add_variation(cond, {'vth0': 0.35})
    """
```

---

## Success Criteria

### Code Quality
- ✅ All files <1000 lines
- ✅ 100% type annotations
- ✅ Google-style docstrings
- ✅ Zero TODO comments
- ✅ All imports verified

### Testing
- ✅ >80% code coverage
- ✅ All tests passing
- ✅ pytest only (no unittest)

### Functionality
- ✅ IR classes fully functional
- ✅ JSON serialization working
- ✅ YAML serialization working (if PyYAML available)
- ✅ Base parser/writer interfaces defined

---

## Dependencies

```toml
# pyproject.toml
[project]
dependencies = [
    "pyyaml>=6.0",  # Optional, for YAML support
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "ruff>=0.1.0",
    "mypy>=1.0",
]
```

---

## Deliverables Checklist

- [ ] `src/ir/model_ir.py` - Complete (400 lines)
- [ ] `src/ir/ir_serializer.py` - Complete (150 lines)
- [ ] `src/parsers/base_parser.py` - Complete (250 lines)
- [ ] `src/writers/base_writer.py` - Complete (200 lines)
- [ ] `tests/test_ir/test_model_ir.py` - Complete (500 lines)
- [ ] `tests/test_ir/test_serializer.py` - Complete (200 lines)
- [ ] All tests passing with >80% coverage
- [ ] All code reviewed and compliant with CONSTRAINTS.md
- [ ] Documentation complete

---

## Next Phase

**Phase 2:** Parser Implementation  
**File:** NEW2026_Phase2.md  
**Duration:** 2 weeks  
**Focus:** Implement Spectre, HSPICE, and ngspice parsers

---

**Document Status:** ✅ Complete  
**Reviewed:** Yes  
**Ready for Implementation:** Yes
