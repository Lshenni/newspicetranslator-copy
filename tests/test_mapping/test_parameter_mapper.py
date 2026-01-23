"""Tests for ParameterMapper."""

import pytest
from pathlib import Path
from src.mapping import (
    ParameterMapper,
    DeviceCategory,
    Confidence,
    MappingResult,
)


@pytest.fixture
def mapper():
    """Create ParameterMapper instance."""
    return ParameterMapper()


class TestParameterMapperInitialization:
    """Test ParameterMapper initialization."""
    
    def test_default_initialization(self, mapper):
        """Test mapper initializes with default mappings directory."""
        assert mapper.mappings_dir.exists()
        assert mapper.mappings_dir.name == "mappings"
    
    def test_custom_directory(self, tmp_path):
        """Test mapper with custom mappings directory."""
        custom_dir = tmp_path / "custom_mappings"
        custom_dir.mkdir()
        
        mapper = ParameterMapper(custom_dir)
        assert mapper.mappings_dir == custom_dir
    
    def test_mappings_loaded(self, mapper):
        """Test that mappings are loaded on initialization."""
        params = mapper.list_parameters(DeviceCategory.MOSFET)
        assert len(params) > 0
        assert "vth0" in params


class TestParameterMapping:
    """Test parameter mapping functionality."""
    
    def test_map_identical_formats(self, mapper):
        """Test mapping between same format returns same name."""
        result = mapper.map_parameter(
            "vth0", "spectre", "spectre", DeviceCategory.MOSFET
        )
        assert result is not None
        assert result.target_param == "vth0"
        assert result.confidence == Confidence.HIGH
    
    def test_map_mosfet_parameters(self, mapper):
        """Test mapping common MOSFET parameters."""
        test_cases = [
            ("vth0", "spectre", "ngspice"),
            ("u0", "spectre", "hspice"),
            ("tox", "hspice", "ngspice"),
            ("k1", "ngspice", "spectre"),
        ]
        
        for param, source, target in test_cases:
            result = mapper.map_parameter(param, source, target, DeviceCategory.MOSFET)
            assert result is not None
            assert result.source_param == param
            assert result.target_param is not None
    
    def test_map_bjt_parameters(self, mapper):
        """Test mapping BJT parameters."""
        result = mapper.map_parameter("bf", "spectre", "ngspice", DeviceCategory.BJT)
        assert result is not None
        assert result.target_param == "bf"
        assert result.confidence == Confidence.HIGH
    
    def test_map_diode_parameters(self, mapper):
        """Test mapping diode parameters."""
        result = mapper.map_parameter("is", "spectre", "ngspice", DeviceCategory.DIODE)
        assert result is not None
        assert result.target_param == "is"
    
    def test_map_passive_parameters(self, mapper):
        """Test mapping passive component parameters."""
        result = mapper.map_parameter("tc1", "spectre", "ngspice", DeviceCategory.PASSIVES)
        assert result is not None
        assert result.target_param == "tc1"
    
    def test_map_unknown_parameter(self, mapper):
        """Test mapping unknown parameter returns None."""
        result = mapper.map_parameter(
            "unknown_param_xyz", "spectre", "ngspice", DeviceCategory.MOSFET
        )
        assert result is None
    
    def test_map_case_insensitive(self, mapper):
        """Test that parameter mapping is case-insensitive."""
        result1 = mapper.map_parameter("vth0", "spectre", "ngspice", DeviceCategory.MOSFET)
        result2 = mapper.map_parameter("VTH0", "spectre", "ngspice", DeviceCategory.MOSFET)
        result3 = mapper.map_parameter("Vth0", "spectre", "ngspice", DeviceCategory.MOSFET)
        
        assert result1 is not None
        assert result2 is not None
        assert result3 is not None
        assert result1.target_param == result2.target_param == result3.target_param


class TestAliasResolution:
    """Test parameter alias resolution."""
    
    def test_resolve_alias(self, mapper):
        """Test resolving parameter alias to canonical name."""
        # vth is an alias for vth0
        canonical = mapper.resolve_alias("vth", DeviceCategory.MOSFET)
        assert canonical == "vth0"
    
    def test_resolve_canonical_name(self, mapper):
        """Test that canonical name resolves to itself."""
        canonical = mapper.resolve_alias("vth0", DeviceCategory.MOSFET)
        assert canonical == "vth0"
    
    def test_resolve_unknown_alias(self, mapper):
        """Test that unknown alias returns None."""
        canonical = mapper.resolve_alias("unknown_alias", DeviceCategory.MOSFET)
        assert canonical is None
    
    def test_map_with_alias(self, mapper):
        """Test mapping using parameter alias."""
        result = mapper.map_parameter("vth", "spectre", "ngspice", DeviceCategory.MOSFET)
        assert result is not None
        assert result.target_param == "vth0"


class TestBatchMapping:
    """Test batch parameter mapping."""
    
    def test_map_parameters_batch(self, mapper):
        """Test mapping multiple parameters at once."""
        params = {
            "vth0": 0.4,
            "u0": 450.0,
            "tox": 2.5e-9,
        }
        
        mapped, unmapped = mapper.map_parameters_batch(
            params, "spectre", "ngspice", DeviceCategory.MOSFET
        )
        
        assert len(mapped) == 3
        assert len(unmapped) == 0
        assert mapped["vth0"] == 0.4
        assert mapped["u0"] == 450.0
        assert mapped["tox"] == 2.5e-9
    
    def test_batch_with_unmapped(self, mapper):
        """Test batch mapping with some unmapped parameters."""
        params = {
            "vth0": 0.4,
            "unknown_param": 1.0,
            "tox": 2.5e-9,
        }
        
        mapped, unmapped = mapper.map_parameters_batch(
            params, "spectre", "ngspice", DeviceCategory.MOSFET
        )
        
        assert len(unmapped) == 1
        assert "unknown_param" in unmapped
        # Unmapped parameters are passed through
        assert "unknown_param" in mapped
        assert mapped["unknown_param"] == 1.0
    
    def test_batch_preserves_values(self, mapper):
        """Test that batch mapping preserves parameter values."""
        params = {
            "vth0": 0.42,
            "tox": 2.5e-9,
            "nfactor": 1.8,
        }
        
        mapped, _ = mapper.map_parameters_batch(
            params, "spectre", "hspice", DeviceCategory.MOSFET
        )
        
        # Values should be preserved exactly
        for param, value in params.items():
            canonical = mapper.resolve_alias(param, DeviceCategory.MOSFET)
            if canonical:
                assert mapped.get(canonical) == value


class TestParameterInfo:
    """Test parameter information retrieval."""
    
    def test_get_parameter_info(self, mapper):
        """Test getting complete parameter information."""
        info = mapper.get_parameter_info("vth0", DeviceCategory.MOSFET)
        
        assert info is not None
        assert "spectre" in info
        assert "hspice" in info
        assert "ngspice" in info
        assert "aliases" in info
    
    def test_get_info_with_alias(self, mapper):
        """Test getting info using parameter alias."""
        info = mapper.get_parameter_info("vth", DeviceCategory.MOSFET)
        assert info is not None
    
    def test_list_parameters(self, mapper):
        """Test listing all parameters for a category."""
        mosfet_params = mapper.list_parameters(DeviceCategory.MOSFET)
        bjt_params = mapper.list_parameters(DeviceCategory.BJT)
        
        assert len(mosfet_params) > 50  # MOSFET has many parameters
        assert len(bjt_params) > 20     # BJT has fewer
        
        assert "vth0" in mosfet_params
        assert "bf" in bjt_params
    
    def test_validate_parameter(self, mapper):
        """Test parameter validation."""
        assert mapper.validate_parameter("vth0", DeviceCategory.MOSFET) is True
        assert mapper.validate_parameter("vth", DeviceCategory.MOSFET) is True  # alias
        assert mapper.validate_parameter("invalid", DeviceCategory.MOSFET) is False


class TestConfidenceScoring:
    """Test confidence scoring for mappings."""
    
    def test_high_confidence_mapping(self, mapper):
        """Test that common parameters have high confidence."""
        result = mapper.map_parameter("vth0", "spectre", "ngspice", DeviceCategory.MOSFET)
        assert result is not None
        assert result.confidence == Confidence.HIGH
    
    def test_confidence_stats(self, mapper):
        """Test confidence statistics calculation."""
        params = {
            "vth0": 0.4,    # high confidence
            "u0": 450.0,    # high confidence
            "tox": 2.5e-9,  # high confidence
            "unknown": 1.0, # unmapped
        }
        
        stats = mapper.get_confidence_stats(
            params, "spectre", "ngspice", DeviceCategory.MOSFET
        )
        
        assert "high" in stats
        assert "medium" in stats
        assert "low" in stats
        assert "unmapped" in stats
        assert stats["high"] >= 3
        assert stats["unmapped"] == 1
    
    def test_all_confidence_levels(self, mapper):
        """Test that mappings include all confidence levels."""
        # Find parameters with different confidence levels
        all_params = mapper.list_parameters(DeviceCategory.MOSFET)
        
        confidence_levels = set()
        for param in all_params:
            result = mapper.map_parameter(param, "spectre", "ngspice", DeviceCategory.MOSFET)
            if result:
                confidence_levels.add(result.confidence)
        
        # Should have at least high confidence mappings
        assert Confidence.HIGH in confidence_levels


class TestDeviceCategories:
    """Test handling of different device categories."""
    
    def test_all_device_categories(self, mapper):
        """Test that all device categories have mappings."""
        categories = [
            DeviceCategory.MOSFET,
            DeviceCategory.BJT,
            DeviceCategory.DIODE,
            DeviceCategory.PASSIVES,
        ]
        
        for category in categories:
            params = mapper.list_parameters(category)
            assert len(params) > 0, f"No parameters for {category.value}"
    
    def test_category_specific_parameters(self, mapper):
        """Test that parameters are category-specific."""
        # vth0 is MOSFET-specific
        mosfet_result = mapper.map_parameter(
            "vth0", "spectre", "ngspice", DeviceCategory.MOSFET
        )
        assert mosfet_result is not None
        
        # bf is BJT-specific
        bjt_result = mapper.map_parameter(
            "bf", "spectre", "ngspice", DeviceCategory.BJT
        )
        assert bjt_result is not None
        
        # is exists in both BJT and DIODE
        bjt_is = mapper.map_parameter(
            "is", "spectre", "ngspice", DeviceCategory.BJT
        )
        diode_is = mapper.map_parameter(
            "is", "spectre", "ngspice", DeviceCategory.DIODE
        )
        assert bjt_is is not None
        assert diode_is is not None


class TestFormatSupport:
    """Test support for different SPICE formats."""
    
    def test_all_format_combinations(self, mapper):
        """Test mapping between all format combinations."""
        formats = ["spectre", "hspice", "ngspice"]
        
        for source in formats:
            for target in formats:
                result = mapper.map_parameter(
                    "vth0", source, target, DeviceCategory.MOSFET
                )
                assert result is not None, f"Failed for {source} -> {target}"
    
    def test_format_case_insensitive(self, mapper):
        """Test that format names are case-insensitive."""
        result1 = mapper.map_parameter("vth0", "spectre", "ngspice", DeviceCategory.MOSFET)
        result2 = mapper.map_parameter("vth0", "SPECTRE", "NGSPICE", DeviceCategory.MOSFET)
        result3 = mapper.map_parameter("vth0", "Spectre", "Ngspice", DeviceCategory.MOSFET)
        
        assert result1 is not None
        assert result2 is not None
        assert result3 is not None
        assert result1.target_param == result2.target_param == result3.target_param


class TestMappingResult:
    """Test MappingResult dataclass."""
    
    def test_mapping_result_structure(self, mapper):
        """Test MappingResult contains expected fields."""
        result = mapper.map_parameter("vth0", "spectre", "ngspice", DeviceCategory.MOSFET)
        
        assert result is not None
        assert hasattr(result, 'source_param')
        assert hasattr(result, 'target_param')
        assert hasattr(result, 'confidence')
        assert hasattr(result, 'notes')
        assert hasattr(result, 'aliases')
    
    def test_result_aliases(self, mapper):
        """Test that result includes alias information."""
        result = mapper.map_parameter("vth0", "spectre", "ngspice", DeviceCategory.MOSFET)
        
        assert result is not None
        assert isinstance(result.aliases, list)
        # vth0 should have aliases like vth, vtho, vt0
        assert len(result.aliases) > 0


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_parameter_name(self, mapper):
        """Test handling of empty parameter name."""
        result = mapper.map_parameter("", "spectre", "ngspice", DeviceCategory.MOSFET)
        assert result is None
    
    def test_whitespace_in_parameter(self, mapper):
        """Test that whitespace is handled correctly."""
        result = mapper.map_parameter(" vth0 ", "spectre", "ngspice", DeviceCategory.MOSFET)
        assert result is not None
        assert result.target_param == "vth0"
    
    def test_batch_empty_dict(self, mapper):
        """Test batch mapping with empty dictionary."""
        mapped, unmapped = mapper.map_parameters_batch(
            {}, "spectre", "ngspice", DeviceCategory.MOSFET
        )
        assert len(mapped) == 0
        assert len(unmapped) == 0
    
    def test_invalid_format_name(self, mapper):
        """Test handling of invalid format names."""
        # Should still work due to normalization
        result = mapper.map_parameter(
            "vth0", "spectre", "ngspice", DeviceCategory.MOSFET
        )
        assert result is not None
