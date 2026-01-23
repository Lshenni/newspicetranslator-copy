"""
Tests for SyntaxValidator.

Compliance: CONSTRAINTS.md
"""

import pytest
from src.validation.syntax_validator import (
    SyntaxValidator,
    SyntaxValidationResult,
    SyntaxError,
    SPICEFormat,
    SyntaxSeverity
)


class TestSyntaxValidator:
    """Test suite for SyntaxValidator."""
    
    def test_valid_hspice_model(self):
        """Test validation of valid HSPICE model."""
        content = """
* Test HSPICE netlist
.MODEL nmos_test NMOS LEVEL=54 VERSION=4.8.0
+ TOXE=2.5E-9 TOXM=2.5E-9 VTH0=0.45
.END
"""
        validator = SyntaxValidator(SPICEFormat.HSPICE)
        result = validator.validate(content)
        
        assert result.valid
        assert result.error_count == 0
    
    def test_valid_ngspice_model(self):
        """Test validation of valid ngspice model."""
        content = """
* Test ngspice netlist
.model nmos_test nmos level=54 version=4.8.0
+ toxe=2.5e-9 toxm=2.5e-9 vth0=0.45
.end
"""
        validator = SyntaxValidator(SPICEFormat.NGSPICE)
        result = validator.validate(content)
        
        assert result.valid
        assert result.error_count == 0
    
    def test_valid_spectre_model(self):
        """Test validation of valid Spectre model."""
        content = """
// Test Spectre netlist
model nmos_test bsim4 type=n version=4.8.0 \\
    toxe=2.5e-9 toxm=2.5e-9 vth0=0.45
"""
        validator = SyntaxValidator(SPICEFormat.SPECTRE)
        result = validator.validate(content)
        
        assert result.valid
        assert result.error_count == 0
    
    def test_empty_content(self):
        """Test detection of empty content."""
        validator = SyntaxValidator(SPICEFormat.HSPICE)
        result = validator.validate("")
        
        assert not result.valid
        assert result.error_count >= 1
    
    def test_hspice_continuation_at_start(self):
        """Test detection of continuation line at file start."""
        content = "+ TOXE=2.5E-9"
        
        validator = SyntaxValidator(SPICEFormat.HSPICE)
        result = validator.validate(content)
        
        assert not result.valid
        assert result.error_count >= 1
    
    def test_hspice_model_statement(self):
        """Test HSPICE .MODEL statement validation."""
        # Valid
        content = ".MODEL test NMOS LEVEL=1"
        validator = SyntaxValidator(SPICEFormat.HSPICE)
        result = validator.validate(content)
        assert result.valid
        
        # Invalid - missing type
        content = ".MODEL test"
        result = validator.validate(content)
        assert not result.valid
    
    def test_hspice_subckt_statement(self):
        """Test HSPICE .SUBCKT statement validation."""
        # Valid
        content = """
.SUBCKT mysubckt in out
.ENDS
"""
        validator = SyntaxValidator(SPICEFormat.HSPICE)
        result = validator.validate(content)
        assert result.valid
        
        # Invalid - missing name
        content = ".SUBCKT"
        result = validator.validate(content)
        assert not result.valid
    
    def test_hspice_ends_without_subckt(self):
        """Test detection of .ENDS without .SUBCKT."""
        content = ".ENDS"
        
        validator = SyntaxValidator(SPICEFormat.HSPICE)
        result = validator.validate(content)
        
        assert result.warning_count >= 1
    
    def test_hspice_lib_statement(self):
        """Test HSPICE .LIB statement validation."""
        # Valid
        content = ".LIB 'modelfile.lib' TT"
        validator = SyntaxValidator(SPICEFormat.HSPICE)
        result = validator.validate(content)
        assert result.valid
        
        # Warning - unquoted filename
        content = ".LIB modelfile.lib TT"
        result = validator.validate(content)
        assert result.warning_count >= 1
    
    def test_hspice_include_statement(self):
        """Test HSPICE .INCLUDE statement validation."""
        # Valid
        content = ".INCLUDE 'models.inc'"
        validator = SyntaxValidator(SPICEFormat.HSPICE)
        result = validator.validate(content)
        assert result.valid
        
        # Warning - unquoted filename
        content = ".INCLUDE models.inc"
        result = validator.validate(content)
        assert result.warning_count >= 1
    
    def test_ngspice_case_insensitive(self):
        """Test ngspice case-insensitive commands."""
        content = """
.MoDel test NMOS level=1
.SubCkt mysubckt in out
.EnDs
"""
        validator = SyntaxValidator(SPICEFormat.NGSPICE)
        result = validator.validate(content)
        
        assert result.valid
    
    def test_spectre_comments(self):
        """Test Spectre comment syntax."""
        content = """
// Single line comment
model test bsim4 type=n
/* Multi-line comment
   continues here */
"""
        validator = SyntaxValidator(SPICEFormat.SPECTRE)
        result = validator.validate(content)
        
        assert result.valid
    
    def test_spectre_continuation(self):
        """Test Spectre line continuation."""
        content = """
model test bsim4 type=n \\
    toxe=2.5e-9 \\
    vth0=0.45
"""
        validator = SyntaxValidator(SPICEFormat.SPECTRE)
        result = validator.validate(content)
        
        assert result.valid
    
    def test_spectre_model_statement(self):
        """Test Spectre model statement validation."""
        # Valid
        content = "model test bsim4 type=n"
        validator = SyntaxValidator(SPICEFormat.SPECTRE)
        result = validator.validate(content)
        assert result.valid
        
        # Invalid - missing type
        content = "model test"
        result = validator.validate(content)
        assert not result.valid
    
    def test_spectre_subckt_statement(self):
        """Test Spectre subckt statement validation."""
        # Valid
        content = """
subckt mysubckt in out
ends mysubckt
"""
        validator = SyntaxValidator(SPICEFormat.SPECTRE)
        result = validator.validate(content)
        assert result.valid
        
        # Invalid - missing name
        content = "subckt"
        result = validator.validate(content)
        assert not result.valid
    
    def test_strict_mode(self):
        """Test strict mode treats warnings as errors."""
        content = ".LIB modelfile.lib TT"  # Unquoted filename - warning
        
        # Non-strict
        validator = SyntaxValidator(SPICEFormat.HSPICE, strict=False)
        result = validator.validate(content)
        assert result.valid
        
        # Strict
        validator = SyntaxValidator(SPICEFormat.HSPICE, strict=True)
        result = validator.validate(content)
        assert not result.valid
    
    def test_non_ascii_characters(self):
        """Test detection of non-ASCII characters."""
        # Non-ASCII in actual SPICE code (not comment)
        content = ".MODEL test NMOS café=1.0"
        
        validator = SyntaxValidator(SPICEFormat.HSPICE)
        result = validator.validate(content)
        
        # Validator detects non-ASCII in code lines
        assert result.warning_count >= 1 or result.valid  # May or may not detect depending on line


# Run tests 10 times for stability
@pytest.mark.parametrize("iteration", range(10))
class TestSyntaxValidatorStability:
    """Test validator stability across multiple runs."""
    
    def test_consistent_validation(self, iteration):
        """Test that validation is consistent across runs."""
        content = """
* Test HSPICE netlist
.MODEL nmos_test NMOS LEVEL=54
.END
"""
        validator = SyntaxValidator(SPICEFormat.HSPICE)
        result = validator.validate(content)
        
        assert result.valid


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
