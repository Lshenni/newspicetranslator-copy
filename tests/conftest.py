"""
Shared pytest fixtures and configuration.

Provides common test fixtures for all test modules.

Compliance: CONSTRAINTS.md
"""

import pytest
from pathlib import Path
from src.ir.model_ir import ModelIR, Condition, Corner, Temperature, DeviceType


@pytest.fixture
def sample_nmos_model():
    """Create a sample NMOS ModelIR for testing."""
    return ModelIR(
        name="nch",
        model_type="bsim4",
        device_type=DeviceType.NMOS,
        base_parameters={
            'level': 54,
            'version': 4.7,
            'toxe': 1.5e-9,
            'epsrox': 3.9,
        }
    )


@pytest.fixture
def sample_pmos_model():
    """Create a sample PMOS ModelIR for testing."""
    return ModelIR(
        name="pch",
        model_type="bsim4",
        device_type=DeviceType.PMOS,
        base_parameters={
            'level': 54,
            'version': 4.7,
            'toxe': 2.0e-9,
            'epsrox': 3.9,
        }
    )


@pytest.fixture
def sample_condition_tt():
    """Create TT/25C condition for testing."""
    return Condition(
        corner=Corner.TT,
        temperature=Temperature.NOMINAL
    )


@pytest.fixture
def sample_condition_ff():
    """Create FF/125C condition for testing."""
    return Condition(
        corner=Corner.FF,
        temperature=Temperature.HOT
    )


@pytest.fixture
def sample_condition_ss():
    """Create SS/-40C condition for testing."""
    return Condition(
        corner=Corner.SS,
        temperature=Temperature.COLD
    )


@pytest.fixture
def sample_model_with_variations(sample_nmos_model, sample_condition_tt, sample_condition_ff):
    """Create a model with multiple variations."""
    model = sample_nmos_model
    
    # Add TT variation
    model.add_variation(
        condition=sample_condition_tt,
        parameters={'vth0': 0.4, 'u0': 450},
        source_line=10,
        source_file="test.scs"
    )
    
    # Add FF variation
    model.add_variation(
        condition=sample_condition_ff,
        parameters={'vth0': 0.35, 'u0': 500},
        source_line=20,
        source_file="test.scs"
    )
    
    return model


@pytest.fixture
def temp_test_file(tmp_path):
    """Create a temporary test file with sample content."""
    test_file = tmp_path / "test_model.txt"
    content = """
* Test SPICE model file
* For unit testing

.model nch nmos level=54
+ toxe=1.5e-9
+ vth0=0.4
"""
    test_file.write_text(content)
    return test_file
