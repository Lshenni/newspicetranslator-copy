"""
Tests to achieve 100% coverage on writer modules.

These tests target the specific uncovered lines in each writer:
- hspice_writer.py line 155: params = {} when corner not found
- ngspice_writer.py line 152: params = {} when corner not found  
- spectre_writer.py line 152: params = {} when corner not found

The uncovered code path occurs when:
1. A corner is requested (corner != None)
2. The model has conditions, but none match the requested corner
3. The `else: params = {}` branch is executed
"""

import pytest
from pathlib import Path
from src.ir.model_ir import (
    ModelIR,
    DeviceType,
    Condition,
    Corner,
    Temperature,
)
from src.writers.hspice_writer import HSPICEWriter
from src.writers.ngspice_writer import NgspiceWriter
from src.writers.spectre_writer import SpectreWriter


class TestHSPICEWriterFullCoverage:
    """Test to achieve 100% coverage on HSPICE writer (line 155)."""

    def test_format_model_corner_not_in_conditions(self, tmp_path: Path) -> None:
        """
        Test writing model when requested corner doesn't exist in model conditions.
        
        This hits line 155 in hspice_writer.py: `params = {}`
        The scenario: corner is not None, but no matching condition is found,
        so condition stays None and the else branch (params = {}) is executed.
        """
        # Create output file
        output_file = tmp_path / "test.sp"
        writer = HSPICEWriter(output_file)

        # Create model with some conditions (but not FF)
        model = ModelIR(
            model_type="bsim4",
            name="test_model",
            device_type=DeviceType.NMOS,
            base_parameters={"vth0": 0.5, "tox": 3e-9},
        )
        
        # Add only TT and SS corners
        tt_cond = Condition(corner=Corner.TT, temperature=Temperature.NOMINAL)
        ss_cond = Condition(corner=Corner.SS, temperature=Temperature.NOMINAL)
        model.add_variation(tt_cond, {"vth0": 0.45})
        model.add_variation(ss_cond, {"vth0": 0.55})

        # Now request FF corner which doesn't exist in the model
        # This should trigger the `else: params = {}` branch on line 155
        result = writer._format_model(model, corner=Corner.FF)
        
        # Should return empty params - model line with no parameters
        assert isinstance(result, list)
        assert len(result) > 0
        # The model line should exist but with no parameters from variations
        assert ".model" in result[0].lower()
        assert "test_model" in result[0].lower()

    def test_format_model_corner_not_found_multiple_conditions(
        self, tmp_path: Path
    ) -> None:
        """
        Test with multiple conditions, none matching requested corner.
        
        This ensures line 155 is hit when there are multiple conditions
        to iterate through, but none match.
        """
        output_file = tmp_path / "test.sp"
        writer = HSPICEWriter(output_file)

        model = ModelIR(
            model_type="bsim4",
            name="complex_model",
            device_type=DeviceType.PMOS,
            base_parameters={"vth0": -0.5},
        )
        
        # Add multiple conditions (TT, SS, FS, SF) but not FF
        variations = {Corner.TT: -0.45, Corner.SS: -0.55, Corner.FS: -0.48, Corner.SF: -0.52}
        for corner, vth0_value in variations.items():
            cond = Condition(corner=corner, temperature=Temperature.NOMINAL)
            model.add_variation(cond, {"vth0": vth0_value})

        # Request FF corner which doesn't exist
        result = writer._format_model(model, corner=Corner.FF)
        
        assert isinstance(result, list)
        assert ".model" in result[0].lower()
        # Should generate output with empty params for FF corner


class TestNgspiceWriterFullCoverage:
    """Test to achieve 100% coverage on ngspice writer (line 152)."""

    def test_format_model_corner_not_in_conditions(self, tmp_path: Path) -> None:
        """
        Test writing model when requested corner doesn't exist in model conditions.
        
        This hits line 152 in ngspice_writer.py: `params = {}`
        """
        output_file = tmp_path / "test.cir"
        writer = NgspiceWriter(output_file)

        model = ModelIR(
            model_type="bsim4",
            name="ngspice_test",
            device_type=DeviceType.NMOS,
            base_parameters={"vth0": 0.5, "tox": 3e-9},
        )
        
        # Add only TT corner
        tt_cond = Condition(corner=Corner.TT, temperature=Temperature.NOMINAL)
        model.add_variation(tt_cond, {"vth0": 0.45})

        # Request FF corner which doesn't exist
        result = writer._format_model(model, corner=Corner.FF)
        
        # ngspice returns string not list
        assert isinstance(result, str)
        assert ".model" in result.lower()
        assert "ngspice_test" in result.lower()

    def test_format_model_nonexistent_corner_with_many_conditions(
        self, tmp_path: Path
    ) -> None:
        """
        Test line 152 with model having many conditions, none matching requested corner.
        """
        output_file = tmp_path / "test.cir"
        writer = NgspiceWriter(output_file)

        model = ModelIR(
            model_type="bsim4",
            name="multi_corner_model",
            device_type=DeviceType.PMOS,
            base_parameters={"vth0": -0.5, "u0": 400},
        )
        
        # Add TT, SS, FS corners but not FF
        for corner in [Corner.TT, Corner.SS, Corner.FS]:
            cond = Condition(corner=corner, temperature=Temperature.NOMINAL)
            model.add_variation(cond, {"vth0": -0.48})

        # Request FF - should hit else branch (params = {}) on line 152
        result = writer._format_model(model, corner=Corner.FF)
        
        # ngspice returns string not list
        assert isinstance(result, str)
        assert ".model" in result.lower()


class TestSpectreWriterFullCoverage:
    """Test to achieve 100% coverage on Spectre writer (line 152)."""

    def test_format_model_corner_not_in_conditions(self, tmp_path: Path) -> None:
        """
        Test writing model when requested corner doesn't exist in model conditions.
        
        This hits line 152 in spectre_writer.py: `params = {}`
        """
        output_file = tmp_path / "test.scs"
        writer = SpectreWriter(output_file)

        model = ModelIR(
            model_type="bsim4",
            name="spectre_test",
            device_type=DeviceType.NMOS,
            base_parameters={"vth0": 0.5, "tox": 3e-9},
        )
        
        # Add only SS corner
        ss_cond = Condition(corner=Corner.SS, temperature=Temperature.NOMINAL)
        model.add_variation(ss_cond, {"vth0": 0.55})

        # Request FF corner which doesn't exist
        result = writer._format_model(model, corner=Corner.FF)
        
        # spectre returns string not list
        assert isinstance(result, str)
        assert "model" in result.lower()
        assert "spectre_test" in result.lower()

    def test_format_model_missing_corner_comprehensive(
        self, tmp_path: Path
    ) -> None:
        """
        Test line 152 comprehensively - model with several corners, request one that's missing.
        """
        output_file = tmp_path / "test.scs"
        writer = SpectreWriter(output_file)

        model = ModelIR(
            model_type="bsim4",
            name="comprehensive_model",
            device_type=DeviceType.PMOS,
            base_parameters={"vth0": -0.5, "tox": 2.5e-9, "u0": 400},
        )
        
        # Add multiple corners except FF
        for corner in [Corner.TT, Corner.SS, Corner.SF]:
            cond = Condition(corner=corner, temperature=Temperature.NOMINAL)
            model.add_variation(cond, {"vth0": -0.48, "u0": 380})

        # Request FF corner - hits else branch on line 152
        result = writer._format_model(model, corner=Corner.FF)
        
        # spectre returns string not list
        assert isinstance(result, str)
        assert "model" in result.lower()
        assert "comprehensive_model" in result.lower()

    def test_format_model_all_corners_missing_requested(
        self, tmp_path: Path
    ) -> None:
        """
        Edge case: model has many conditions, but requested corner exists in NONE of them.
        """
        output_file = tmp_path / "test.scs"
        writer = SpectreWriter(output_file)

        model = ModelIR(
            model_type="bsim4",
            name="edge_case_model",
            device_type=DeviceType.NMOS,
            base_parameters={"vth0": 0.5},
        )
        
        # Add ALL corners EXCEPT FF
        variations = {Corner.TT: 0.50, Corner.SS: 0.55, Corner.FS: 0.48, Corner.SF: 0.52}
        for corner, vth0_value in variations.items():
            cond = Condition(corner=corner, temperature=Temperature.NOMINAL)
            model.add_variation(cond, {"vth0": vth0_value})

        # Request the one corner we didn't add (FF)
        result = writer._format_model(model, corner=Corner.FF)
        
        # spectre returns string not list
        assert isinstance(result, str)
        assert "model" in result.lower()


# Additional integration test to verify all writers together
class TestAllWriters100Coverage:
    """Integration test to verify 100% coverage across all three writers."""

    @pytest.mark.parametrize(
        "writer_class,output_ext,keyword",
        [
            (HSPICEWriter, ".sp", ".model"),
            (NgspiceWriter, ".cir", ".model"),
            (SpectreWriter, ".scs", "model"),
        ],
    )
    def test_all_writers_missing_corner_coverage(
        self, tmp_path: Path, writer_class, output_ext: str, keyword: str
    ) -> None:
        """
        Parametrized test to hit the missing coverage line in all three writers.
        
        This test covers:
        - hspice_writer.py line 155
        - ngspice_writer.py line 152
        - spectre_writer.py line 152
        
        All by requesting a corner that doesn't exist in the model.
        """
        output_file = tmp_path / f"test{output_ext}"
        writer = writer_class(output_file)

        model = ModelIR(
            model_type="bsim4",
            name="parametrized_test_model",
            device_type=DeviceType.NMOS,
            base_parameters={"vth0": 0.5, "tox": 3e-9},
        )
        
        # Add only TT and SS corners
        for corner in [Corner.TT, Corner.SS]:
            cond = Condition(corner=corner, temperature=Temperature.NOMINAL)
            model.add_variation(cond, {"vth0": 0.48})

        # Request FF corner which doesn't exist in any condition
        # This triggers the `else: params = {}` branch in all writers
        result = writer._format_model(model, corner=Corner.FF)
        
        # HSPICE returns list, ngspice/spectre return string
        if isinstance(result, list):
            assert len(result) > 0
            result_str = result[0].lower()
        else:
            result_str = result.lower()
        
        assert keyword in result_str
        assert "parametrized_test_model" in result_str
