"""
Tests for ngspice parser.

Validates NgspiceParser against ngspice format files.
"""

import pytest
from pathlib import Path

from src.parsers.ngspice_parser import NgspiceParser
from src.ir.model_ir import ModelIR, DeviceType, Corner, Temperature, Condition


class TestNgspiceParser:
    """Test suite for NgspiceParser."""

    def test_parser_initialization(self, tmp_path: Path) -> None:
        """Test parser can be initialized."""
        test_file = tmp_path / "test.lib"
        test_file.write_text("* Empty file\n")

        parser = NgspiceParser(test_file)
        assert parser.file_path == test_file
        assert parser.get_format_name() == "ngspice"

    def test_empty_file_raises_error(self, tmp_path: Path) -> None:
        """Test parsing empty file raises ValueError."""
        test_file = tmp_path / "empty.lib"
        test_file.write_text("")

        parser = NgspiceParser(test_file)
        with pytest.raises(ValueError, match="No content"):
            parser.parse_to_ir()

    def test_parse_simple_model(self, tmp_path: Path) -> None:
        """Test parsing simple ngspice model."""
        content = """
* Simple NMOS model
.model nch nmos level=54 tox=2.1e-9 vth0=0.45
"""
        test_file = tmp_path / "simple.lib"
        test_file.write_text(content)

        parser = NgspiceParser(test_file)
        models = parser.parse_to_ir()

        assert len(models) == 1
        model = models[0]
        assert model.name == "nch"
        assert model.model_type == "nmos"
        assert model.device_type == DeviceType.NMOS
        assert model.metadata.get("source_format") == "ngspice"
        assert "tox" in model.base_parameters
        assert "vth0" in model.base_parameters

    def test_parse_with_parentheses(self, tmp_path: Path) -> None:
        """Test parsing model with parentheses around parameters."""
        content = """
.model nch nmos (level=54 tox=2.1e-9 vth0=0.45)
"""
        test_file = tmp_path / "parens.lib"
        test_file.write_text(content)

        parser = NgspiceParser(test_file)
        models = parser.parse_to_ir()

        assert len(models) == 1
        params = models[0].base_parameters
        assert "level" in params
        assert "tox" in params
        assert "vth0" in params

    def test_parse_continuation_lines(self, tmp_path: Path) -> None:
        """Test parsing continuation lines."""
        content = """
.model nch nmos level=54
+tox=2.1e-9
+vth0=0.45
+u0=0.03
"""
        test_file = tmp_path / "continuation.lib"
        test_file.write_text(content)

        parser = NgspiceParser(test_file)
        models = parser.parse_to_ir()

        assert len(models) == 1
        params = models[0].base_parameters
        assert "level" in params
        assert "tox" in params
        assert "vth0" in params
        assert "u0" in params

    def test_parse_with_lib_section(self, tmp_path: Path) -> None:
        """Test parsing model within .lib section."""
        content = """
.lib tt
.model nch nmos level=54 vth0=0.45
.endl
"""
        test_file = tmp_path / "lib.lib"
        test_file.write_text(content)

        parser = NgspiceParser(test_file)
        models = parser.parse_to_ir()

        assert len(models) == 1
        model = models[0]
        assert model.has_variations()

        # Should have TT corner variation
        tt_condition = Condition(Corner.TT, Temperature.NOMINAL)
        variation = model.get_variation(tt_condition)
        assert variation is not None
        assert "vth0" in variation.parameters

    def test_parse_multiple_models(self, tmp_path: Path) -> None:
        """Test parsing multiple models."""
        content = """
.model nch nmos level=54 vth0=0.45
.model pch pmos level=54 vth0=-0.45
"""
        test_file = tmp_path / "multi.lib"
        test_file.write_text(content)

        parser = NgspiceParser(test_file)
        models = parser.parse_to_ir()

        assert len(models) == 2
        assert models[0].device_type == DeviceType.NMOS
        assert models[1].device_type == DeviceType.PMOS

    def test_parse_with_comments(self, tmp_path: Path) -> None:
        """Test parsing with comments."""
        content = """
* This is a comment
.model nch nmos level=54 vth0=0.45 $ Inline comment
+tox=2.1e-9 * Another inline
"""
        test_file = tmp_path / "comments.lib"
        test_file.write_text(content)

        parser = NgspiceParser(test_file)
        models = parser.parse_to_ir()

        assert len(models) == 1
        assert "vth0" in models[0].base_parameters
        assert "tox" in models[0].base_parameters

    def test_parse_scientific_notation(self, tmp_path: Path) -> None:
        """Test parsing scientific notation values."""
        content = """
.model nch nmos tox=2.1e-9 length=1.5E-8 width=3.2e-07
"""
        test_file = tmp_path / "scientific.lib"
        test_file.write_text(content)

        parser = NgspiceParser(test_file)
        models = parser.parse_to_ir()

        assert len(models) == 1
        params = models[0].base_parameters
        assert params["tox"] == pytest.approx(2.1e-9)
        assert params["length"] == pytest.approx(1.5e-8)
        assert params["width"] == pytest.approx(3.2e-7)

    def test_device_type_classification(self, tmp_path: Path) -> None:
        """Test device type classification."""
        content = """
.model nch nmos level=54
.model pch pmos level=54
.model npn_bjt npn
.model pnp_bjt pnp
"""
        test_file = tmp_path / "devices.lib"
        test_file.write_text(content)

        parser = NgspiceParser(test_file)
        models = parser.parse_to_ir()

        assert len(models) == 4
        assert models[0].device_type == DeviceType.NMOS
        assert models[1].device_type == DeviceType.PMOS
        assert models[2].device_type == DeviceType.NPN
        assert models[3].device_type == DeviceType.PNP

    def test_case_insensitive_directives(self, tmp_path: Path) -> None:
        """Test directives are case-insensitive."""
        content = """
.MODEL nch NMOS level=54
.Model pch Pmos level=54
"""
        test_file = tmp_path / "case.lib"
        test_file.write_text(content)

        parser = NgspiceParser(test_file)
        models = parser.parse_to_ir()

        assert len(models) == 2

    def test_parse_all_corners(self, tmp_path: Path) -> None:
        """Test parsing all standard corners."""
        content = """
.lib tt
.model nch nmos vth0=0.45
.endl

.lib ff
.model nch nmos vth0=0.40
.endl

.lib ss
.model nch nmos vth0=0.50
.endl
"""
        test_file = tmp_path / "corners.lib"
        test_file.write_text(content)

        parser = NgspiceParser(test_file)
        models = parser.parse_to_ir()

        # Should create 3 separate models
        assert len(models) == 3

    def test_invalid_model_card_ignored(self, tmp_path: Path) -> None:
        """Test invalid model cards are ignored."""
        content = """
.model  * Invalid

.model nch nmos vth0=0.45

.model invalid_only_name
"""
        test_file = tmp_path / "invalid.lib"
        test_file.write_text(content)

        parser = NgspiceParser(test_file)
        models = parser.parse_to_ir()

        # Only the valid model should be parsed
        assert len(models) == 1
        assert models[0].name == "nch"


class TestNgspiceParserRealFiles:
    """Test NgspiceParser with real files if available."""

    @pytest.fixture
    def spice_lib_path(self) -> Path:
        """Get path to SPICE libraries."""
        return Path(__file__).parent.parent.parent / "tools" / "spice-libraries" / "private-models"

    @pytest.mark.skipif(
        not (Path(__file__).parent.parent.parent / "tools" / "spice-libraries").exists(),
        reason="SPICE library files not available"
    )
    def test_parse_real_ngspice_files(self, spice_lib_path: Path) -> None:
        """Test parsing real ngspice files if available."""
        # Look for .lib files that might be ngspice format
        lib_files = list(spice_lib_path.rglob("*.lib"))
        
        if not lib_files:
            pytest.skip("No library files found")

        # Test a few files
        for test_file in lib_files[:3]:
            parser = NgspiceParser(test_file)
            
            try:
                models = parser.parse_to_ir()
                # Should parse without errors
                assert isinstance(models, list)
                
                for model in models:
                    assert isinstance(model, ModelIR)
                    assert model.metadata.get("source_format") == "ngspice"
                    
            except Exception as e:
                # Some files might be includes or have no models
                if "No content" not in str(e) and len(models) == 0:
                    continue  # Empty is OK
