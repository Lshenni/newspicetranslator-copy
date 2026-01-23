"""
Unit tests for ModelIR and related classes.

Tests all IR components thoroughly to ensure correctness.

Compliance: CONSTRAINTS.md - pytest only
"""

import pytest
from pathlib import Path
from src.ir.model_ir import (
    ModelIR, Condition, ModelVariation, Corner, Temperature, DeviceType
)


class TestCorner:
    """Test Corner enum."""
    
    def test_corner_values(self):
        """Test that all corners have correct values."""
        assert Corner.TT.value == "typical-typical"
        assert Corner.FF.value == "fast-fast"
        assert Corner.SS.value == "slow-slow"
        assert Corner.FS.value == "fast-slow"
        assert Corner.SF.value == "slow-fast"
    
    def test_from_string_standard(self):
        """Test conversion from standard strings."""
        assert Corner.from_string('tt') == Corner.TT
        assert Corner.from_string('TT') == Corner.TT
        assert Corner.from_string('ff') == Corner.FF
        assert Corner.from_string('FF') == Corner.FF
        assert Corner.from_string('ss') == Corner.SS
        assert Corner.from_string('fs') == Corner.FS
        assert Corner.from_string('sf') == Corner.SF
    
    def test_from_string_verbose(self):
        """Test conversion from verbose strings."""
        assert Corner.from_string('typical-typical') == Corner.TT
        assert Corner.from_string('fast-fast') == Corner.FF
        assert Corner.from_string('slow-slow') == Corner.SS
        assert Corner.from_string('fast-slow') == Corner.FS
        assert Corner.from_string('slow-fast') == Corner.SF
    
    def test_from_string_invalid(self):
        """Test that invalid strings raise ValueError."""
        with pytest.raises(ValueError, match="Unknown corner"):
            Corner.from_string('invalid')
        with pytest.raises(ValueError):
            Corner.from_string('xyz')


class TestTemperature:
    """Test Temperature enum."""
    
    def test_temperature_values(self):
        """Test that temperatures have correct values."""
        assert Temperature.COLD.value == -40
        assert Temperature.NOMINAL.value == 25
        assert Temperature.HOT.value == 125
    
    def test_from_celsius_exact(self):
        """Test conversion from exact values."""
        assert Temperature.from_celsius(-40) == Temperature.COLD
        assert Temperature.from_celsius(25) == Temperature.NOMINAL
        assert Temperature.from_celsius(125) == Temperature.HOT
    
    def test_from_celsius_nearest(self):
        """Test conversion to nearest temperature."""
        assert Temperature.from_celsius(-50) == Temperature.COLD
        assert Temperature.from_celsius(0) == Temperature.NOMINAL
        assert Temperature.from_celsius(20) == Temperature.NOMINAL
        assert Temperature.from_celsius(30) == Temperature.NOMINAL
        assert Temperature.from_celsius(100) == Temperature.HOT
        assert Temperature.from_celsius(150) == Temperature.HOT


class TestCondition:
    """Test Condition class."""
    
    def test_condition_creation(self):
        """Test basic condition creation."""
        cond = Condition(
            corner=Corner.TT,
            temperature=Temperature.NOMINAL
        )
        assert cond.corner == Corner.TT
        assert cond.temperature == Temperature.NOMINAL
        assert cond.voltage is None
    
    def test_condition_with_voltage(self):
        """Test condition with voltage."""
        cond = Condition(
            corner=Corner.FF,
            temperature=Temperature.HOT,
            voltage=1.8
        )
        assert cond.voltage == 1.8
    
    def test_condition_str(self):
        """Test string representation."""
        cond1 = Condition(Corner.TT, Temperature.NOMINAL)
        assert str(cond1) == "TT_25C"
        
        cond2 = Condition(Corner.FF, Temperature.HOT, voltage=1.8)
        assert str(cond2) == "FF_125C_1.8V"
    
    def test_condition_equality(self):
        """Test condition equality."""
        cond1 = Condition(Corner.TT, Temperature.NOMINAL)
        cond2 = Condition(Corner.TT, Temperature.NOMINAL)
        cond3 = Condition(Corner.FF, Temperature.NOMINAL)
        
        assert cond1 == cond2
        assert cond1 != cond3
    
    def test_condition_hashable(self):
        """Test that conditions can be used in sets/dicts."""
        cond1 = Condition(Corner.TT, Temperature.NOMINAL)
        cond2 = Condition(Corner.FF, Temperature.HOT)
        
        cond_set = {cond1, cond2, cond1}  # Duplicate cond1
        assert len(cond_set) == 2
        
        cond_dict = {cond1: "value1", cond2: "value2"}
        assert cond_dict[cond1] == "value1"
    
    def test_to_spectre_section(self):
        """Test conversion to Spectre section name."""
        cond = Condition(Corner.TT, Temperature.NOMINAL)
        assert cond.to_spectre_section() == "tt"
        
        cond2 = Condition(Corner.FF, Temperature.HOT)
        assert cond2.to_spectre_section() == "ff"
    
    def test_to_hspice_lib(self):
        """Test conversion to HSPICE library name."""
        cond1 = Condition(Corner.TT, Temperature.COLD)
        assert cond1.to_hspice_lib() == "tt_n40"
        
        cond2 = Condition(Corner.FF, Temperature.NOMINAL)
        assert cond2.to_hspice_lib() == "ff_25"
        
        cond3 = Condition(Corner.SS, Temperature.HOT)
        assert cond3.to_hspice_lib() == "ss_125"
    
    def test_to_ngspice_lib(self):
        """Test conversion to ngspice library name."""
        cond1 = Condition(Corner.TT, Temperature.COLD)
        assert cond1.to_ngspice_lib() == "tt_t-40"
        
        cond2 = Condition(Corner.FF, Temperature.NOMINAL)
        assert cond2.to_ngspice_lib() == "ff_t25"


class TestModelVariation:
    """Test ModelVariation class."""
    
    def test_variation_creation(self):
        """Test basic variation creation."""
        cond = Condition(Corner.TT, Temperature.NOMINAL)
        params = {'vth0': 0.4, 'tox': 1.5e-9}
        
        var = ModelVariation(
            condition=cond,
            parameters=params,
            source_line=10,
            source_file="test.scs"
        )
        
        assert var.condition == cond
        assert var.parameters == params
        assert var.source_line == 10
        assert var.source_file == "test.scs"
    
    def test_get_parameter(self):
        """Test parameter retrieval."""
        var = ModelVariation(
            condition=Condition(Corner.TT, Temperature.NOMINAL),
            parameters={'vth0': 0.4, 'tox': 1.5e-9},
            source_line=1,
            source_file="test"
        )
        
        assert var.get_parameter('vth0') == 0.4
        assert var.get_parameter('tox') == 1.5e-9
        assert var.get_parameter('missing') is None
        assert var.get_parameter('missing', default=42) == 42
    
    def test_has_parameter(self):
        """Test parameter existence check."""
        var = ModelVariation(
            condition=Condition(Corner.TT, Temperature.NOMINAL),
            parameters={'vth0': 0.4},
            source_line=1,
            source_file="test"
        )
        
        assert var.has_parameter('vth0')
        assert not var.has_parameter('missing')
    
    def test_to_dict(self):
        """Test serialization to dict."""
        cond = Condition(Corner.TT, Temperature.NOMINAL, voltage=1.8)
        var = ModelVariation(
            condition=cond,
            parameters={'vth0': 0.4},
            source_line=10,
            source_file="test.scs"
        )
        
        d = var.to_dict()
        assert d['condition']['corner'] == 'TT'
        assert d['condition']['temperature'] == 25
        assert d['condition']['voltage'] == 1.8
        assert d['parameters'] == {'vth0': 0.4}
        assert d['source_line'] == 10
        assert d['source_file'] == "test.scs"
    
    def test_from_dict(self):
        """Test deserialization from dict."""
        data = {
            'condition': {
                'corner': 'FF',
                'temperature': 125,
                'voltage': 1.8
            },
            'parameters': {'vth0': 0.35},
            'source_line': 20,
            'source_file': 'test.sp'
        }
        
        var = ModelVariation.from_dict(data)
        assert var.condition.corner == Corner.FF
        assert var.condition.temperature == Temperature.HOT
        assert var.condition.voltage == 1.8
        assert var.parameters == {'vth0': 0.35}


class TestModelIR:
    """Test ModelIR class."""
    
    def test_model_creation_basic(self):
        """Test basic model creation."""
        model = ModelIR(
            name="nch",
            model_type="bsim4",
            device_type=DeviceType.NMOS
        )
        
        assert model.name == "nch"
        assert model.model_type == "bsim4"
        assert model.device_type == DeviceType.NMOS
        assert model.base_parameters == {}
        assert model.variations == []
    
    def test_model_with_parameters(self):
        """Test model with base parameters."""
        params = {
            'level': 54,
            'version': 4.7,
            'toxe': 1.5e-9
        }
        
        model = ModelIR(
            name="nch",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters=params
        )
        
        assert model.base_parameters == params
    
    def test_add_variation(self):
        """Test adding variations."""
        model = ModelIR(
            name="nch",
            model_type="bsim4",
            device_type=DeviceType.NMOS
        )
        
        cond_tt = Condition(Corner.TT, Temperature.NOMINAL)
        cond_ff = Condition(Corner.FF, Temperature.HOT)
        
        model.add_variation(
            condition=cond_tt,
            parameters={'vth0': 0.4},
            source_line=10,
            source_file="test.scs"
        )
        
        model.add_variation(
            condition=cond_ff,
            parameters={'vth0': 0.35},
            source_line=20,
            source_file="test.scs"
        )
        
        assert len(model.variations) == 2
        assert model.has_variations()
    
    def test_get_variation(self):
        """Test retrieving specific variation."""
        model = ModelIR(
            name="nch",
            model_type="bsim4",
            device_type=DeviceType.NMOS
        )
        
        cond = Condition(Corner.TT, Temperature.NOMINAL)
        model.add_variation(cond, {'vth0': 0.4})
        
        var = model.get_variation(cond)
        assert var is not None
        assert var.parameters == {'vth0': 0.4}
        
        # Non-existent condition
        cond_missing = Condition(Corner.FF, Temperature.HOT)
        assert model.get_variation(cond_missing) is None
    
    def test_get_all_parameters(self):
        """Test parameter merging."""
        model = ModelIR(
            name="nch",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={'toxe': 1.5e-9, 'vth0': 0.4}
        )
        
        # Get base only
        params_base = model.get_all_parameters()
        assert params_base == {'toxe': 1.5e-9, 'vth0': 0.4}
        
        # Add variation that overrides vth0
        cond = Condition(Corner.FF, Temperature.HOT)
        model.add_variation(cond, {'vth0': 0.35, 'u0': 450})
        
        # Get merged parameters
        params_merged = model.get_all_parameters(cond)
        assert params_merged['toxe'] == 1.5e-9  # From base
        assert params_merged['vth0'] == 0.35    # Override from variation
        assert params_merged['u0'] == 450       # New from variation
    
    def test_get_conditions(self):
        """Test retrieving all conditions."""
        model = ModelIR(
            name="nch",
            model_type="bsim4",
            device_type=DeviceType.NMOS
        )
        
        cond1 = Condition(Corner.TT, Temperature.NOMINAL)
        cond2 = Condition(Corner.FF, Temperature.HOT)
        
        model.add_variation(cond1, {'vth0': 0.4})
        model.add_variation(cond2, {'vth0': 0.35})
        
        conditions = model.get_conditions()
        assert len(conditions) == 2
        assert cond1 in conditions
        assert cond2 in conditions
    
    def test_to_dict(self):
        """Test serialization to dict."""
        model = ModelIR(
            name="nch",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={'toxe': 1.5e-9},
            metadata={'source_format': 'spectre'}
        )
        
        cond = Condition(Corner.TT, Temperature.NOMINAL)
        model.add_variation(cond, {'vth0': 0.4}, 10, "test.scs")
        
        d = model.to_dict()
        assert d['name'] == 'nch'
        assert d['model_type'] == 'bsim4'
        assert d['device_type'] == 'nmos'
        assert d['base_parameters'] == {'toxe': 1.5e-9}
        assert len(d['variations']) == 1
        assert d['metadata'] == {'source_format': 'spectre'}
    
    def test_from_dict(self):
        """Test deserialization from dict."""
        data = {
            'name': 'pch',
            'model_type': 'bsim4',
            'device_type': 'pmos',
            'base_parameters': {'toxe': 1.5e-9},
            'variations': [
                {
                    'condition': {
                        'corner': 'TT',
                        'temperature': 25,
                        'voltage': None
                    },
                    'parameters': {'vth0': -0.4},
                    'source_line': 10,
                    'source_file': 'test.scs'
                }
            ],
            'subcircuit_content': None,
            'metadata': {}
        }
        
        model = ModelIR.from_dict(data)
        assert model.name == 'pch'
        assert model.model_type == 'bsim4'
        assert model.device_type == DeviceType.PMOS
        assert model.base_parameters == {'toxe': 1.5e-9}
        assert len(model.variations) == 1
    
    def test_repr(self):
        """Test string representation."""
        model = ModelIR(
            name="nch",
            model_type="bsim4",
            device_type=DeviceType.NMOS
        )
        
        repr_str = repr(model)
        assert "nch" in repr_str
        assert "bsim4" in repr_str
        assert "nmos" in repr_str
