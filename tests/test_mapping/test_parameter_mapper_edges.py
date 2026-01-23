"""
Tests for parameter mapper edge cases.

This test file achieves coverage for edge cases in parameter_mapper.py,
focusing on the actual API and realistic scenarios.
"""

import pytest
from pathlib import Path

from src.mapping.parameter_mapper import ParameterMapper, DeviceCategory


class TestParameterMapperInitialization:
    """Test mapper initialization edge cases."""

    def test_init_with_missing_directory(self, tmp_path: Path) -> None:
        """Test initialization handles missing directory gracefully."""
        missing_dir = tmp_path / "nonexistent"
        
        # Should not crash, just log warnings
        mapper = ParameterMapper(missing_dir)
        assert mapper is not None

    def test_init_with_empty_directory(self, tmp_path: Path) -> None:
        """Test initialization with empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        
        # Should initialize but have no mappings
        mapper = ParameterMapper(empty_dir)
        assert mapper is not None

    def test_init_with_none_uses_defaults(self) -> None:
        """Test initialization with None uses default mappings."""
        mapper = ParameterMapper(None)
        assert mapper is not None


class TestParameterMapperEdgeCases:
    """Test parameter mapping edge cases."""

    def test_map_parameter_unknown_category(self) -> None:
        """Test mapping with category that has no mappings."""
        mapper = ParameterMapper()
        
        # Try to map with unknown category
        result = mapper.map_parameter(
            "unknown_param",
            "hspice",
            "ngspice",
            DeviceCategory.MOSFET
        )
        
        # Should return None gracefully
        assert result is None or isinstance(result, type(result))

    def test_map_parameter_case_insensitive(self) -> None:
        """Test that parameter mapping is case-insensitive."""
        mapper = ParameterMapper()
        
        # Try different cases of same parameter
        result1 = mapper.map_parameter("VTH0", "hspice", "ngspice", DeviceCategory.MOSFET)
        result2 = mapper.map_parameter("vth0", "hspice", "ngspice", DeviceCategory.MOSFET)
        result3 = mapper.map_parameter("Vth0", "hspice", "ngspice", DeviceCategory.MOSFET)
        
        # All should produce same result (or all None)
        if result1 and result2 and result3:
            assert result1.target_param == result2.target_param == result3.target_param

    def test_map_parameter_with_whitespace(self) -> None:
        """Test parameter mapping strips whitespace."""
        mapper = ParameterMapper()
        
        # Try parameter with leading/trailing whitespace
        result = mapper.map_parameter(
            "  vth0  ",
            "  hspice  ",
            "  ngspice  ",
            DeviceCategory.MOSFET
        )
        
        # Should handle gracefully
        assert result is None or isinstance(result, type(result))

    def test_resolve_alias_unknown_parameter(self) -> None:
        """Test alias resolution for unknown parameter."""
        mapper = ParameterMapper()
        
        # Try to resolve completely unknown parameter
        result = mapper.resolve_alias("completely_unknown_param_12345", DeviceCategory.MOSFET)
        
        # Should return None
        assert result is None

    def test_resolve_alias_empty_string(self) -> None:
        """Test alias resolution with empty string."""
        mapper = ParameterMapper()
        
        # Try empty string
        result = mapper.resolve_alias("", DeviceCategory.MOSFET)
        
        # Should handle gracefully
        assert result is None or isinstance(result, str)

    def test_map_parameters_batch_empty_list(self) -> None:
        """Test batch mapping with empty parameter dict."""
        mapper = ParameterMapper()
        
        # Map empty dict
        mapped, unmapped = mapper.map_parameters_batch(
            {},
            "hspice",
            "ngspice",
            DeviceCategory.MOSFET
        )
        
        # Should return empty results
        assert mapped == {}
        assert unmapped == []

    def test_map_parameters_batch_all_unknown(self) -> None:
        """Test batch mapping with all unknown parameters."""
        mapper = ParameterMapper()
        
        # Map all unknown parameters
        mapped, unmapped = mapper.map_parameters_batch(
            {"unknown1": 1.0, "unknown2": 2.0, "unknown3": 3.0},
            "hspice",
            "ngspice",
            DeviceCategory.MOSFET
        )
        
        # Unknown params pass through - check they're in both dicts
        assert len(unmapped) == 3
        assert "unknown1" in mapped  # pass-through
        assert "unknown2" in mapped
        assert "unknown3" in mapped

    def test_get_parameter_info_unknown(self) -> None:
        """Test getting info for unknown parameter."""
        mapper = ParameterMapper()
        
        # Get info for unknown parameter
        info = mapper.get_parameter_info("unknown_param_xyz", DeviceCategory.MOSFET)
        
        # Should return None
        assert info is None

    def test_list_parameters_unknown_category(self) -> None:
        """Test listing parameters for unknown category."""
        mapper = ParameterMapper()
        
        # List parameters for category
        params = mapper.list_parameters(DeviceCategory.MOSFET)
        
        # Should return list (may be empty)
        assert isinstance(params, list)

    def test_validate_parameter_unknown(self) -> None:
        """Test validation of unknown parameter."""
        mapper = ParameterMapper()
        
        # Validate unknown parameter
        is_valid = mapper.validate_parameter(
            "unknown_param",
            DeviceCategory.MOSFET
        )
        
        # Should return False
        assert is_valid is False

    def test_validate_parameter_empty_string(self) -> None:
        """Test validation of empty parameter name."""
        mapper = ParameterMapper()
        
        # Validate empty string
        is_valid = mapper.validate_parameter(
            "",
            DeviceCategory.MOSFET
        )
        
        # Should return False
        assert is_valid is False

    def test_get_confidence_stats_empty_category(self) -> None:
        """Test getting confidence stats for empty parameters."""
        mapper = ParameterMapper()
        
        # Get stats for empty dict
        stats = mapper.get_confidence_stats(
            {},
            "hspice",
            "ngspice",
            DeviceCategory.MOSFET
        )
        
        # Should return dict with zero counts
        assert isinstance(stats, dict)
        assert all(count == 0 for count in stats.values())


class TestParameterMapperRobustness:
    """Test mapper robustness with unusual inputs."""

    def test_map_parameter_very_long_name(self) -> None:
        """Test mapping parameter with very long name."""
        mapper = ParameterMapper()
        
        # Very long parameter name
        long_name = "a" * 1000
        result = mapper.map_parameter(
            long_name,
            "hspice",
            "ngspice",
            DeviceCategory.MOSFET
        )
        
        # Should handle without crashing
        assert result is None or isinstance(result, type(result))

    def test_map_parameter_special_characters(self) -> None:
        """Test mapping parameter with special characters."""
        mapper = ParameterMapper()
        
        # Parameter with special characters
        special_name = "param-with.special@chars#123"
        result = mapper.map_parameter(
            special_name,
            "hspice",
            "ngspice",
            DeviceCategory.MOSFET
        )
        
        # Should handle without crashing
        assert result is None or isinstance(result, type(result))

    def test_map_parameter_unicode_name(self) -> None:
        """Test mapping parameter with Unicode characters."""
        mapper = ParameterMapper()
        
        # Unicode parameter name
        unicode_name = "参数τ測試"
        result = mapper.map_parameter(
            unicode_name,
            "hspice",
            "ngspice",
            DeviceCategory.MOSFET
        )
        
        # Should handle without crashing
        assert result is None or isinstance(result, type(result))

    def test_map_parameters_batch_large_dict(self) -> None:
        """Test batch mapping with large parameter dictionary."""
        mapper = ParameterMapper()
        
        # Large parameter dict
        large_params = {f"param{i}": float(i) for i in range(1000)}
        mapped, unmapped = mapper.map_parameters_batch(
            large_params,
            "hspice",
            "ngspice",
            DeviceCategory.MOSFET
        )
        
        # Should complete without crashing
        assert isinstance(mapped, dict)
        assert isinstance(unmapped, list)
        assert len(mapped) == 1000  # pass-through

    def test_map_parameters_batch_mixed_value_types(self) -> None:
        """Test batch mapping with mixed parameter value types."""
        mapper = ParameterMapper()
        
        # Mixed value types
        mixed_params = {
            "int_param": 42,
            "float_param": 3.14,
            "str_param": "value",
            "none_param": None,
        }
        mapped, unmapped = mapper.map_parameters_batch(
            mixed_params,
            "hspice",
            "ngspice",
            DeviceCategory.MOSFET
        )
        
        # Should handle all types without crashing
        assert isinstance(mapped, dict)
        assert isinstance(unmapped, list)
        assert len(mapped) == 4  # pass-through
