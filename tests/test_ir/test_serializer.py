"""
Unit tests for IR serialization.

Tests JSON and YAML serialization/deserialization.

Compliance: CONSTRAINTS.md - pytest only
"""

import pytest
import json
from pathlib import Path
from src.ir.model_ir import ModelIR, Condition, Corner, Temperature, DeviceType
from src.ir.ir_serializer import IRSerializer


class TestJSONSerialization:
    """Test JSON serialization."""
    
    def test_single_model_to_json(self):
        """Test serializing single model to JSON."""
        model = ModelIR(
            name="nch",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={'toxe': 1.5e-9}
        )
        
        json_str = IRSerializer.to_json(model)
        data = json.loads(json_str)
        
        assert data['name'] == 'nch'
        assert data['model_type'] == 'bsim4'
        assert data['base_parameters']['toxe'] == 1.5e-9
    
    def test_multiple_models_to_json(self):
        """Test serializing multiple models to JSON."""
        models = [
            ModelIR(name="nch", model_type="bsim4", device_type=DeviceType.NMOS),
            ModelIR(name="pch", model_type="bsim4", device_type=DeviceType.PMOS),
        ]
        
        json_str = IRSerializer.to_json(models)
        data = json.loads(json_str)
        
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]['name'] == 'nch'
        assert data[1]['name'] == 'pch'
    
    def test_from_json_single(self):
        """Test deserializing single model from JSON."""
        json_str = '''
        {
            "name": "nch",
            "model_type": "bsim4",
            "device_type": "nmos",
            "base_parameters": {"toxe": 1.5e-9},
            "variations": [],
            "subcircuit_content": null,
            "metadata": {}
        }
        '''
        
        model = IRSerializer.from_json(json_str)
        assert isinstance(model, ModelIR)
        assert model.name == "nch"
        assert model.base_parameters['toxe'] == 1.5e-9
    
    def test_from_json_multiple(self):
        """Test deserializing multiple models from JSON."""
        json_str = '''
        [
            {
                "name": "nch",
                "model_type": "bsim4",
                "device_type": "nmos",
                "base_parameters": {},
                "variations": [],
                "subcircuit_content": null,
                "metadata": {}
            },
            {
                "name": "pch",
                "model_type": "bsim4",
                "device_type": "pmos",
                "base_parameters": {},
                "variations": [],
                "subcircuit_content": null,
                "metadata": {}
            }
        ]
        '''
        
        models = IRSerializer.from_json(json_str)
        assert isinstance(models, list)
        assert len(models) == 2
        assert models[0].name == "nch"
        assert models[1].name == "pch"
    
    def test_round_trip_json(self):
        """Test JSON serialization round trip."""
        original = ModelIR(
            name="nch",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={'toxe': 1.5e-9, 'vth0': 0.4}
        )
        
        cond = Condition(Corner.TT, Temperature.NOMINAL)
        original.add_variation(cond, {'u0': 450}, 10, "test.scs")
        
        # Serialize and deserialize
        json_str = IRSerializer.to_json(original)
        restored = IRSerializer.from_json(json_str)
        
        assert restored.name == original.name
        assert restored.model_type == original.model_type
        assert restored.device_type == original.device_type
        assert restored.base_parameters == original.base_parameters
        assert len(restored.variations) == 1
    
    def test_json_file_operations(self, tmp_path):
        """Test JSON file read/write."""
        model = ModelIR(
            name="test_model",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={'toxe': 1.5e-9}
        )
        
        file_path = tmp_path / "test_model.json"
        
        # Write to file
        IRSerializer.to_json_file(model, file_path)
        assert file_path.exists()
        
        # Read from file
        loaded = IRSerializer.from_json_file(file_path)
        assert loaded.name == model.name
        assert loaded.base_parameters == model.base_parameters


class TestYAMLSerialization:
    """Test YAML serialization."""
    
    def test_yaml_available(self):
        """Test if YAML is available."""
        try:
            import yaml
            assert True
        except ImportError:
            pytest.skip("PyYAML not available")
    
    def test_single_model_to_yaml(self):
        """Test serializing single model to YAML."""
        pytest.importorskip("yaml")
        
        model = ModelIR(
            name="nch",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={'toxe': 1.5e-9}
        )
        
        yaml_str = IRSerializer.to_yaml(model)
        assert 'name: nch' in yaml_str
        assert 'model_type: bsim4' in yaml_str
    
    def test_from_yaml(self):
        """Test deserializing from YAML."""
        pytest.importorskip("yaml")
        
        yaml_str = '''
name: nch
model_type: bsim4
device_type: nmos
base_parameters:
  toxe: 1.5e-9
variations: []
subcircuit_content: null
metadata: {}
        '''
        
        model = IRSerializer.from_yaml(yaml_str)
        assert model.name == "nch"
        assert model.base_parameters['toxe'] == 1.5e-9
    
    def test_round_trip_yaml(self):
        """Test YAML serialization round trip."""
        pytest.importorskip("yaml")
        
        original = ModelIR(
            name="pch",
            model_type="bsim4",
            device_type=DeviceType.PMOS,
            base_parameters={'toxe': 2.0e-9}
        )
        
        yaml_str = IRSerializer.to_yaml(original)
        restored = IRSerializer.from_yaml(yaml_str)
        
        assert restored.name == original.name
        assert restored.base_parameters == original.base_parameters
    
    def test_yaml_file_operations(self, tmp_path):
        """Test YAML file read/write."""
        pytest.importorskip("yaml")
        
        model = ModelIR(
            name="test_yaml",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={'toxe': 1.5e-9}
        )
        
        file_path = tmp_path / "test_model.yaml"
        
        # Write to file
        IRSerializer.to_yaml_file(model, file_path)
        assert file_path.exists()
        
        # Read from file
        loaded = IRSerializer.from_yaml_file(file_path)
        assert loaded.name == model.name


class TestComplexSerialization:
    """Test serialization of complex IR structures."""
    
    def test_model_with_variations(self):
        """Test serializing model with multiple variations."""
        model = ModelIR(
            name="nch",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={'toxe': 1.5e-9}
        )
        
        # Add multiple variations
        cond_tt = Condition(Corner.TT, Temperature.NOMINAL)
        cond_ff = Condition(Corner.FF, Temperature.HOT)
        cond_ss = Condition(Corner.SS, Temperature.COLD)
        
        model.add_variation(cond_tt, {'vth0': 0.4}, 10, "test.scs")
        model.add_variation(cond_ff, {'vth0': 0.35}, 20, "test.scs")
        model.add_variation(cond_ss, {'vth0': 0.45}, 30, "test.scs")
        
        # Round trip
        json_str = IRSerializer.to_json(model)
        restored = IRSerializer.from_json(json_str)
        
        assert len(restored.variations) == 3
        assert restored.get_variation(cond_tt).parameters['vth0'] == 0.4
        assert restored.get_variation(cond_ff).parameters['vth0'] == 0.35
        assert restored.get_variation(cond_ss).parameters['vth0'] == 0.45
    
    def test_multiple_models_with_variations(self):
        """Test serializing multiple complex models."""
        models = []
        
        for device_name in ['nch', 'pch']:
            device_type = DeviceType.NMOS if device_name == 'nch' else DeviceType.PMOS
            model = ModelIR(
                name=device_name,
                model_type="bsim4",
                device_type=device_type,
                base_parameters={'toxe': 1.5e-9}
            )
            
            for corner in [Corner.TT, Corner.FF, Corner.SS]:
                cond = Condition(corner, Temperature.NOMINAL)
                vth = 0.4 if device_name == 'nch' else -0.4
                model.add_variation(cond, {'vth0': vth}, 0, "test")
            
            models.append(model)
        
        # Round trip
        json_str = IRSerializer.to_json(models)
        restored_models = IRSerializer.from_json(json_str)
        
        assert len(restored_models) == 2
        assert all(len(m.variations) == 3 for m in restored_models)
