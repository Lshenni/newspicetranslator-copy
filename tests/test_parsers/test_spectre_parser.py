"""
Tests for Spectre parser with real SPICE model data.

Validates SpectreParser against actual Spectre format files.
"""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.parsers.spectre_parser import SpectreParser
from src.ir.model_ir import ModelIR, DeviceType, Corner, Temperature


class TestSpectreParser:
    """Test suite for SpectreParser."""

    def test_parser_initialization(self, tmp_path: Path) -> None:
        """Test parser can be initialized."""
        test_file = tmp_path / "test.scs"
        test_file.write_text("// Empty file\n")

        parser = SpectreParser(test_file)
        assert parser.file_path == test_file
        assert parser.get_format_name() == "spectre"

    def test_empty_file_raises_error(self, tmp_path: Path) -> None:
        """Test parsing empty file raises ValueError."""
        test_file = tmp_path / "empty.scs"
        test_file.write_text("")

        parser = SpectreParser(test_file)
        with pytest.raises(ValueError, match="No content"):
            parser.parse_to_ir()

    def test_parse_simple_model(self, tmp_path: Path) -> None:
        """Test parsing simple Spectre model."""
        content = """
// Simple NMOS model
model nch bsim4 {
    type = n
    tox = 2.1e-9
    vth0 = 0.45
    u0 = 0.03
}
"""
        test_file = tmp_path / "simple.scs"
        test_file.write_text(content)

        parser = SpectreParser(test_file)
        models = parser.parse_to_ir()

        assert len(models) == 1
        model = models[0]
        assert model.name == "nch"
        assert model.model_type == "bsim4"
        assert model.device_type == DeviceType.NMOS
        assert model.metadata.get("source_format") == "spectre"
        assert "tox" in model.base_parameters
        assert "vth0" in model.base_parameters

    def test_parse_model_with_section(self, tmp_path: Path) -> None:
        """Test parsing model within section (corner)."""
        content = """
section tt {
    model nch bsim4 {
        type = n
        vth0 = 0.45
        tox = 2.1e-9
    }
}
"""
        test_file = tmp_path / "section.scs"
        test_file.write_text(content)

        parser = SpectreParser(test_file)
        models = parser.parse_to_ir()

        assert len(models) == 1
        model = models[0]
        assert model.has_variations()
        
        # Should have TT corner variation
        from src.ir.model_ir import Condition
        tt_condition = Condition(Corner.TT, Temperature.NOMINAL)
        variation = model.get_variation(tt_condition)
        assert variation is not None
        assert "vth0" in variation.parameters
        assert "tox" in variation.parameters

    def test_parse_multiple_models(self, tmp_path: Path) -> None:
        """Test parsing multiple models in one file."""
        content = """
model nch bsim4 {
    type = n
    vth0 = 0.45
}

model pch bsim4 {
    type = p
    vth0 = -0.45
}
"""
        test_file = tmp_path / "multi.scs"
        test_file.write_text(content)

        parser = SpectreParser(test_file)
        models = parser.parse_to_ir()

        assert len(models) == 2
        assert models[0].name == "nch"
        assert models[0].device_type == DeviceType.NMOS
        assert models[1].name == "pch"
        assert models[1].device_type == DeviceType.PMOS

    def test_parse_with_comments(self, tmp_path: Path) -> None:
        """Test parsing with comments."""
        content = """
// This is a comment
model nch bsim4 {  // Inline comment
    type = n       // Another comment
    vth0 = 0.45
    // Parameter comment
    tox = 2.1e-9
}
"""
        test_file = tmp_path / "comments.scs"
        test_file.write_text(content)

        parser = SpectreParser(test_file)
        models = parser.parse_to_ir()

        assert len(models) == 1
        assert "vth0" in models[0].base_parameters

    def test_parse_scientific_notation(self, tmp_path: Path) -> None:
        """Test parsing scientific notation values."""
        content = """
model nch bsim4 {
    tox = 2.1e-9
    length = 1.5E-8
    width = 3.2e-07
}
"""
        test_file = tmp_path / "scientific.scs"
        test_file.write_text(content)

        parser = SpectreParser(test_file)
        models = parser.parse_to_ir()

        assert len(models) == 1
        params = models[0].base_parameters
        assert params["tox"] == pytest.approx(2.1e-9)
        assert params["length"] == pytest.approx(1.5e-8)
        assert params["width"] == pytest.approx(3.2e-7)

    def test_parse_all_corners(self, tmp_path: Path) -> None:
        """Test parsing all standard corners."""
        content = """
section tt {
    model nch bsim4 { vth0 = 0.45 }
}

section ff {
    model nch bsim4 { vth0 = 0.40 }
}

section ss {
    model nch bsim4 { vth0 = 0.50 }
}

section fs {
    model nch bsim4 { vth0 = 0.48 }
}

section sf {
    model nch bsim4 { vth0 = 0.42 }
}
"""
        test_file = tmp_path / "corners.scs"
        test_file.write_text(content)

        parser = SpectreParser(test_file)
        models = parser.parse_to_ir()

        # Should create 5 separate models (one per section)
        assert len(models) == 5

    def test_device_type_classification(self, tmp_path: Path) -> None:
        """Test device type classification."""
        content = """
model nch bsim4 { type = n }
model pch bsim4 { type = p }
model npn_bjt vbic { type = npn }
model diode_model diode { }
"""
        test_file = tmp_path / "devices.scs"
        test_file.write_text(content)

        parser = SpectreParser(test_file)
        models = parser.parse_to_ir()

        assert len(models) == 4
        assert models[0].device_type == DeviceType.NMOS
        assert models[1].device_type == DeviceType.PMOS
        assert models[2].device_type == DeviceType.NPN
        assert models[3].device_type == DeviceType.DIODE

    def test_nested_braces(self, tmp_path: Path) -> None:
        """Test handling of nested braces."""
        content = """
model nch bsim4 {
    vth0 = 0.45
    parameters {
        tox = 2.1e-9
    }
}
"""
        test_file = tmp_path / "nested.scs"
        test_file.write_text(content)

        parser = SpectreParser(test_file)
        models = parser.parse_to_ir()

        # Should handle nested braces gracefully
        assert len(models) == 1

    def test_invalid_model_card_ignored(self, tmp_path: Path) -> None:
        """Test invalid model cards are ignored."""
        content = """
model  // Invalid - no name or type

model nch bsim4 {
    vth0 = 0.45
}

model invalid_only_name
"""
        test_file = tmp_path / "invalid.scs"
        test_file.write_text(content)

        parser = SpectreParser(test_file)
        models = parser.parse_to_ir()

        # Only the valid model should be parsed
        assert len(models) == 1
        assert models[0].name == "nch"


class TestSpectreParserRealFiles:
    """Test SpectreParser with real SPICE library files if available."""

    @pytest.fixture
    def spice_lib_path(self) -> Path:
        """Get path to SPICE libraries."""
        return Path(__file__).parent.parent.parent / "tools" / "spice-libraries" / "private-models"

    @pytest.mark.skipif(
        not (Path(__file__).parent.parent.parent / "tools" / "spice-libraries").exists(),
        reason="SPICE library files not available"
    )
    def test_parse_real_spectre_file(self, spice_lib_path: Path) -> None:
        """Test parsing real Spectre files if available."""
        # Look for .scs files in the library
        scs_files = list(spice_lib_path.rglob("*.scs"))
        
        if scs_files:
            test_file = scs_files[0]
            parser = SpectreParser(test_file)
            
            try:
                models = parser.parse_to_ir()
                # Should parse without errors
                assert isinstance(models, list)
                for model in models:
                    assert isinstance(model, ModelIR)
                    assert model.metadata.get("source_format") == "spectre"
            except Exception as e:
                pytest.fail(f"Failed to parse real Spectre file {test_file}: {e}")
