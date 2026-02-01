"""
Tests for HSPICE parser with real SPICE model data.

Validates HSPICEParser against actual HSPICE format files.
"""

import pytest
from pathlib import Path

from src.parsers.hspice_parser import HSPICEParser
from src.ir.model_ir import ModelIR, DeviceType, Corner, Temperature, Condition


class TestHSPICEParser:
    """Test suite for HSPICEParser."""

    def test_parser_initialization(self, tmp_path: Path) -> None:
        """Test parser can be initialized."""
        test_file = tmp_path / "test.sp"
        test_file.write_text("* Empty file\n")

        parser = HSPICEParser(test_file)
        assert parser.file_path == test_file
        assert parser.get_format_name() == "hspice"

    def test_empty_file_raises_error(self, tmp_path: Path) -> None:
        """Test parsing empty file raises ValueError."""
        test_file = tmp_path / "empty.sp"
        test_file.write_text("")

        parser = HSPICEParser(test_file)
        with pytest.raises(ValueError, match="No content"):
            parser.parse_to_ir()

    def test_parse_simple_model(self, tmp_path: Path) -> None:
        """Test parsing simple HSPICE model."""
        content = """
* Simple NMOS model
.model nmos_lvt nmos level=72 tox=2.1e-9 vth0=0.45 u0=0.03
"""
        test_file = tmp_path / "simple.sp"
        test_file.write_text(content)

        parser = HSPICEParser(test_file)
        models = parser.parse_to_ir()

        assert len(models) == 1
        model = models[0]
        assert model.name == "nmos_lvt"
        assert model.model_type == "nmos"
        assert model.device_type == DeviceType.NMOS
        assert model.metadata.get("source_format") == "hspice"
        assert "tox" in model.base_parameters
        assert "vth0" in model.base_parameters

    def test_parse_continuation_lines(self, tmp_path: Path) -> None:
        """Test parsing continuation lines."""
        content = """
.model nmos_lvt nmos level=72
+tox=2.1e-9
+vth0=0.45
+u0=0.03
"""
        test_file = tmp_path / "continuation.sp"
        test_file.write_text(content)

        parser = HSPICEParser(test_file)
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
.model nmos_lvt nmos level=72 vth0=0.45
.endl
"""
        test_file = tmp_path / "lib.sp"
        test_file.write_text(content)

        parser = HSPICEParser(test_file)
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
.model nmos_lvt nmos level=72 vth0=0.45
.model pmos_lvt pmos level=72 vth0=-0.45
"""
        test_file = tmp_path / "multi.sp"
        test_file.write_text(content)

        parser = HSPICEParser(test_file)
        models = parser.parse_to_ir()

        assert len(models) == 2
        assert models[0].device_type == DeviceType.NMOS
        assert models[1].device_type == DeviceType.PMOS

    def test_parse_with_comments(self, tmp_path: Path) -> None:
        """Test parsing with various comment styles."""
        content = """
* This is a comment
** Another comment
.model nmos_lvt nmos level=72 vth0=0.45 $ Inline comment
+tox=2.1e-9 * Another inline comment
"""
        test_file = tmp_path / "comments.sp"
        test_file.write_text(content)

        parser = HSPICEParser(test_file)
        models = parser.parse_to_ir()

        assert len(models) == 1
        assert "vth0" in models[0].base_parameters
        assert "tox" in models[0].base_parameters

    def test_parse_scientific_notation(self, tmp_path: Path) -> None:
        """Test parsing scientific notation values."""
        content = """
.model nmos_lvt nmos tox=2.1e-9 length=1.5E-8 width=3.2e-07
"""
        test_file = tmp_path / "scientific.sp"
        test_file.write_text(content)

        parser = HSPICEParser(test_file)
        models = parser.parse_to_ir()

        assert len(models) == 1
        params = models[0].base_parameters
        assert params["tox"] == pytest.approx(2.1e-9)
        assert params["length"] == pytest.approx(1.5e-8)
        assert params["width"] == pytest.approx(3.2e-7)

        def test_parse_quoted_expression_with_multiplication_not_truncated(
                self, tmp_path: Path
        ) -> None:
                """Ensure '*' used for multiplication isn't treated as an inline comment.

                This is critical for HSPICE model decks that use quoted expressions like:
                    rb='105.0*(1+drb_foo)'
                """
                content = """
.model npn50a25 npn rb='105.0*(1+drb_npn50a25)' cje='2.2875E-14*(1+dcje_npn50a25)'
"""
                test_file = tmp_path / "quoted_mul.sp"
                test_file.write_text(content)

                parser = HSPICEParser(test_file)
                models = parser.parse_to_ir()
                assert len(models) == 1

                params = models[0].base_parameters
                assert "rb" in params
                assert "cje" in params

                rb = str(params["rb"])
                cje = str(params["cje"])

                assert "drb_npn50a25" in rb
                assert "*" in rb
                assert rb.startswith("'") and rb.endswith("'")

                assert "dcje_npn50a25" in cje
                assert "*" in cje
                assert cje.startswith("'") and cje.endswith("'")

    def test_device_type_classification(self, tmp_path: Path) -> None:
        """Test device type classification."""
        content = """
.model nmos_lvt nmos level=72
.model pmos_rvt pmos level=72
.model npn_model npn
.model pnp_model pnp
"""
        test_file = tmp_path / "devices.sp"
        test_file.write_text(content)

        parser = HSPICEParser(test_file)
        models = parser.parse_to_ir()

        assert len(models) == 4
        assert models[0].device_type == DeviceType.NMOS
        assert models[1].device_type == DeviceType.PMOS
        assert models[2].device_type == DeviceType.NPN
        assert models[3].device_type == DeviceType.PNP

    def test_case_insensitive_directives(self, tmp_path: Path) -> None:
        """Test directives are case-insensitive."""
        content = """
.MODEL nmos_lvt NMOS level=72
.Model pmos_lvt Pmos level=72
"""
        test_file = tmp_path / "case.sp"
        test_file.write_text(content)

        parser = HSPICEParser(test_file)
        models = parser.parse_to_ir()

        assert len(models) == 2

    def test_parse_all_corners(self, tmp_path: Path) -> None:
        """Test parsing all standard corners in lib sections."""
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
        test_file = tmp_path / "corners.sp"
        test_file.write_text(content)

        parser = HSPICEParser(test_file)
        models = parser.parse_to_ir()

        # Should create 3 separate models (one per lib section)
        assert len(models) == 3

    def test_invalid_model_card_ignored(self, tmp_path: Path) -> None:
        """Test invalid model cards are ignored."""
        content = """
.model  * Invalid - no name

.model nmos_lvt nmos vth0=0.45

.model invalid_only_name
"""
        test_file = tmp_path / "invalid.sp"
        test_file.write_text(content)

        parser = HSPICEParser(test_file)
        models = parser.parse_to_ir()

        # Only the valid model should be parsed
        assert len(models) == 1
        assert models[0].name == "nmos_lvt"


class TestHSPICEParserRealFiles:
    """Test HSPICEParser with real SPICE library files."""

    @pytest.fixture
    def spice_lib_path(self) -> Path:
        """Get path to SPICE libraries."""
        return Path(__file__).parent.parent.parent / "tools" / "spice-libraries" / "private-models"

    @pytest.mark.skipif(
        not (Path(__file__).parent.parent.parent / "tools" / "spice-libraries").exists(),
        reason="SPICE library files not available"
    )
    def test_parse_asap7_tt(self, spice_lib_path: Path) -> None:
        """Test parsing ASAP7 TT corner file."""
        test_file = spice_lib_path / "asap7" / "hspice" / "tt.lib"
        
        if not test_file.exists():
            pytest.skip("ASAP7 TT file not found")

        parser = HSPICEParser(test_file)
        models = parser.parse_to_ir()

        # Should parse models from the file
        assert len(models) > 0
        
        for model in models:
            assert isinstance(model, ModelIR)
            assert model.metadata.get("source_format") == "hspice"
            assert model.device_type in list(DeviceType)
            # Should have parameters
            assert len(model.get_all_parameters()) > 0

    @pytest.mark.skipif(
        not (Path(__file__).parent.parent.parent / "tools" / "spice-libraries").exists(),
        reason="SPICE library files not available"
    )
    def test_parse_real_hspice_files(self, spice_lib_path: Path) -> None:
        """Test parsing various real HSPICE files."""
        # Look for .lib and .sp files
        hspice_files = list(spice_lib_path.rglob("*.lib"))
        hspice_files.extend(list(spice_lib_path.rglob("*.sp")))
        
        if not hspice_files:
            pytest.skip("No HSPICE files found")

        # Test first few files
        for test_file in hspice_files[:5]:
            parser = HSPICEParser(test_file)
            
            try:
                models = parser.parse_to_ir()
                # Should parse without errors
                assert isinstance(models, list)
                
                for model in models:
                    assert isinstance(model, ModelIR)
                    assert model.metadata.get("source_format") == "hspice"
                    assert model.name  # Must have a name
                    assert model.model_type  # Must have a base model
                    
            except Exception as e:
                # Some files might be includes only, that's OK
                if "No content" not in str(e):
                    pytest.fail(f"Failed to parse {test_file}: {e}")
