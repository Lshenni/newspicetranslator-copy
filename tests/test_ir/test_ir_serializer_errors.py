"""
Tests for IR serializer error handling.

This test file achieves coverage for error paths in ir_serializer.py.
"""

import pytest
from pathlib import Path
import json
import yaml

from src.ir.ir_serializer import IRSerializer
from src.ir.model_ir import ModelIR, DeviceType


class TestIRSerializerFileErrors:
    """Test file operation error handling."""

    def test_save_json_auto_creates_directories(self, tmp_path: Path) -> None:
        """Test that saving JSON automatically creates parent directories."""
        model = ModelIR(
            name="test",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={"vth0": 0.5}
        )
        
        # Save to non-existent directory (should create it)
        nested_path = tmp_path / "nonexistent" / "subdir" / "test.json"
        
        # Should create directories automatically
        IRSerializer.to_json_file([model], nested_path)
        assert nested_path.exists()

    def test_save_yaml_auto_creates_directories(self, tmp_path: Path) -> None:
        """Test that saving YAML automatically creates parent directories."""
        model = ModelIR(
            name="test",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={"vth0": 0.5}
        )
        
        # Save to non-existent directory (should create it)
        nested_path = tmp_path / "nonexistent" / "subdir" / "test.yaml"
        
        # Should create directories automatically
        IRSerializer.to_yaml_file([model], nested_path)
        assert nested_path.exists()

    def test_load_json_missing_file(self, tmp_path: Path) -> None:
        """Test loading JSON from non-existent file."""
        missing_file = tmp_path / "missing.json"
        
        with pytest.raises(FileNotFoundError):
            IRSerializer.from_json_file(missing_file)

    def test_load_yaml_missing_file(self, tmp_path: Path) -> None:
        """Test loading YAML from non-existent file."""
        missing_file = tmp_path / "missing.yaml"
        
        with pytest.raises(FileNotFoundError):
            IRSerializer.from_yaml_file(missing_file)


class TestIRSerializerMalformedData:
    """Test handling of malformed JSON/YAML data."""

    def test_load_json_malformed_syntax(self, tmp_path: Path) -> None:
        """Test loading JSON with syntax errors."""
        malformed_file = tmp_path / "malformed.json"
        malformed_file.write_text("""
        {
            "name": "test",
            "invalid syntax here
        }
        """)
        
        with pytest.raises(json.JSONDecodeError):
            IRSerializer.from_json_file(malformed_file)

    def test_load_json_invalid_structure(self, tmp_path: Path) -> None:
        """Test loading JSON with invalid IR structure."""
        invalid_file = tmp_path / "invalid.json"
        # Valid JSON but missing required ModelIR fields
        invalid_file.write_text("""
        [
            {
                "name": "test"
            }
        ]
        """)
        
        # Should raise error when trying to construct ModelIR
        with pytest.raises((KeyError, TypeError, ValueError)):
            IRSerializer.from_json_file(invalid_file)

    def test_load_yaml_malformed_syntax(self, tmp_path: Path) -> None:
        """Test loading YAML with syntax errors."""
        malformed_file = tmp_path / "malformed.yaml"
        malformed_file.write_text("""
        - name: test
          invalid: [unclosed bracket
          model_type: bsim4
        """)
        
        with pytest.raises(yaml.YAMLError):
            IRSerializer.from_yaml_file(malformed_file)

    def test_load_yaml_invalid_structure(self, tmp_path: Path) -> None:
        """Test loading YAML with invalid IR structure."""
        invalid_file = tmp_path / "invalid.yaml"
        # Valid YAML but missing required fields
        invalid_file.write_text("""
        - name: test
          # Missing model_type and device_type
        """)
        
        with pytest.raises((KeyError, TypeError, ValueError)):
            IRSerializer.from_yaml_file(invalid_file)

    def test_load_json_empty_file(self, tmp_path: Path) -> None:
        """Test loading empty JSON file."""
        empty_file = tmp_path / "empty.json"
        empty_file.write_text("")
        
        with pytest.raises(json.JSONDecodeError):
            IRSerializer.from_json_file(empty_file)

    def test_load_yaml_empty_file(self, tmp_path: Path) -> None:
        """Test loading empty YAML file."""
        empty_file = tmp_path / "empty.yaml"
        empty_file.write_text("")
        
        # Empty YAML returns None which is invalid
        with pytest.raises(ValueError):
            IRSerializer.from_yaml_file(empty_file)

    def test_load_json_wrong_type(self, tmp_path: Path) -> None:
        """Test loading JSON that's not a list."""
        wrong_type = tmp_path / "wrong.json"
        wrong_type.write_text("""
        {
            "name": "test",
            "model_type": "bsim4"
        }
        """)
        
        # Should expect a list, not a dict - raises KeyError for missing fields
        with pytest.raises((KeyError, TypeError, ValueError)):
            IRSerializer.from_json_file(wrong_type)

    def test_load_yaml_wrong_type(self, tmp_path: Path) -> None:
        """Test loading YAML that's not a list."""
        wrong_type = tmp_path / "wrong.yaml"
        wrong_type.write_text("""
        name: test
        model_type: bsim4
        """)
        
        # Should expect a list, not a dict - raises KeyError for missing fields
        with pytest.raises((KeyError, TypeError, ValueError)):
            IRSerializer.from_yaml_file(wrong_type)


class TestIRSerializerEdgeCases:
    """Test edge cases in serialization."""

    def test_save_empty_model_list(self, tmp_path: Path) -> None:
        """Test saving empty model list."""
        json_file = tmp_path / "empty.json"
        yaml_file = tmp_path / "empty.yaml"
        
        IRSerializer.to_json_file([], json_file)
        IRSerializer.to_yaml_file([], yaml_file)
        
        # Should create valid empty files
        assert json_file.exists()
        assert yaml_file.exists()
        
        loaded_json = IRSerializer.from_json_file(json_file)
        loaded_yaml = IRSerializer.from_yaml_file(yaml_file)
        
        assert loaded_json == []
        assert loaded_yaml == [] or loaded_yaml is None

    def test_roundtrip_with_special_characters(self, tmp_path: Path) -> None:
        """Test serialization with special characters in parameters."""
        model = ModelIR(
            name="test_model",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={
                "special": "value with spaces",
                "unicode": "测试",
                "newline": "line1\nline2",
                "quote": 'value with "quotes"',
            }
        )
        
        json_file = tmp_path / "special.json"
        yaml_file = tmp_path / "special.yaml"
        
        # Should handle special characters
        IRSerializer.to_json_file([model], json_file)
        IRSerializer.to_yaml_file([model], yaml_file)
        
        loaded_json = IRSerializer.from_json_file(json_file)
        loaded_yaml = IRSerializer.from_yaml_file(yaml_file)
        
        assert len(loaded_json) == 1
        assert len(loaded_yaml) == 1

    def test_load_json_with_byte_order_mark(self, tmp_path: Path) -> None:
        """Test loading JSON file with BOM raises error."""
        bom_file = tmp_path / "bom.json"
        # Write JSON with UTF-8 BOM
        bom_file.write_bytes(b'\xef\xbb\xbf[]')
        
        # JSON decoder doesn't handle BOM automatically
        with pytest.raises(json.JSONDecodeError):
            IRSerializer.from_json_file(bom_file)

    def test_save_model_with_none_values(self, tmp_path: Path) -> None:
        """Test saving model with None parameter values."""
        model = ModelIR(
            name="test",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters={"param1": None, "param2": 0.5}
        )
        
        json_file = tmp_path / "none.json"
        yaml_file = tmp_path / "none.yaml"
        
        # Should handle None values
        IRSerializer.to_json_file([model], json_file)
        IRSerializer.to_yaml_file([model], yaml_file)
        
        assert json_file.exists()
        assert yaml_file.exists()

    def test_load_json_with_trailing_comma(self, tmp_path: Path) -> None:
        """Test loading JSON with trailing commas (invalid JSON)."""
        trailing_comma = tmp_path / "trailing.json"
        trailing_comma.write_text('[{"name": "test",}]')
        
        # Should reject invalid JSON
        with pytest.raises(json.JSONDecodeError):
            IRSerializer.from_json_file(trailing_comma)

    def test_large_model_serialization(self, tmp_path: Path) -> None:
        """Test serialization of model with many parameters."""
        large_params = {f"param_{i}": i * 0.001 for i in range(1000)}
        model = ModelIR(
            name="large_model",
            model_type="bsim4",
            device_type=DeviceType.NMOS,
            base_parameters=large_params
        )
        
        json_file = tmp_path / "large.json"
        yaml_file = tmp_path / "large.yaml"
        
        # Should handle large models
        IRSerializer.to_json_file([model], json_file)
        IRSerializer.to_yaml_file([model], yaml_file)
        
        loaded_json = IRSerializer.from_json_file(json_file)
        loaded_yaml = IRSerializer.from_yaml_file(yaml_file)
        
        assert len(loaded_json) == 1
        assert len(loaded_yaml) == 1
        assert len(loaded_json[0].base_parameters) == 1000
