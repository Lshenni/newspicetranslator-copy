"""
Syntax Validator - Validates output SPICE syntax correctness.

Validates that generated SPICE netlists follow proper syntax rules for
HSPICE, ngspice, and Spectre formats.

Compliance: CONSTRAINTS.md
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Set
from enum import Enum
import re
import logging

logger = logging.getLogger(__name__)


class SPICEFormat(Enum):
    """Supported SPICE formats."""
    HSPICE = "hspice"
    NGSPICE = "ngspice"
    SPECTRE = "spectre"


class SyntaxSeverity(Enum):
    """Severity levels for syntax issues."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class SyntaxError:
    """
    Represents a syntax error in SPICE netlist.
    
    Attributes:
        severity: Error severity
        line_number: Line number where error occurred
        line_content: Content of the line
        message: Error description
        suggestion: Suggested fix
    """
    severity: SyntaxSeverity
    line_number: int
    line_content: str
    message: str
    suggestion: Optional[str] = None
    
    def __str__(self) -> str:
        """Format error for display."""
        parts = [f"[{self.severity.value.upper()}]"]
        parts.append(f"Line {self.line_number}:")
        parts.append(f"{self.message}")
        if self.suggestion:
            parts.append(f"(Suggestion: {self.suggestion})")
        parts.append(f"\n  > {self.line_content.strip()}")
        return " ".join(parts)


@dataclass
class SyntaxValidationResult:
    """
    Result of syntax validation.
    
    Attributes:
        valid: True if no errors found
        format: SPICE format being validated
        errors: List of syntax errors
        warnings: List of syntax warnings
        info: List of informational messages
    """
    valid: bool
    format: SPICEFormat
    errors: List[SyntaxError]
    warnings: List[SyntaxError]
    info: List[SyntaxError]
    
    @property
    def error_count(self) -> int:
        """Number of errors."""
        return len(self.errors)
    
    @property
    def warning_count(self) -> int:
        """Number of warnings."""
        return len(self.warnings)
    
    def __str__(self) -> str:
        """Format validation result."""
        if self.valid:
            return f"✓ {self.format.value} syntax valid ({self.warning_count} warnings, {len(self.info)} info)"
        return f"✗ {self.format.value} syntax invalid ({self.error_count} errors, {self.warning_count} warnings)"


class SyntaxValidator:
    """
    Validates SPICE syntax correctness.
    
    Supports HSPICE, ngspice, and Spectre formats.
    Checks:
    - Model card syntax
    - Subcircuit definitions
    - Parameter declarations
    - Library statements
    - Comment syntax
    - Line continuation
    """
    
    def __init__(self, format: SPICEFormat, strict: bool = False) -> None:
        """
        Initialize validator.
        
        Args:
            format: Target SPICE format
            strict: If True, treat warnings as errors
        """
        self.format = format
        self.strict = strict
        self.errors: List[SyntaxError] = []
        self.warnings: List[SyntaxError] = []
        self.info: List[SyntaxError] = []
    
    def validate(self, content: str) -> SyntaxValidationResult:
        """
        Validate SPICE netlist syntax.
        
        Args:
            content: SPICE netlist content as string
            
        Returns:
            Validation result
        """
        self.errors = []
        self.warnings = []
        self.info = []
        
        if not content or not content.strip():
            self.errors.append(SyntaxError(
                severity=SyntaxSeverity.ERROR,
                line_number=0,
                line_content="",
                message="Empty netlist content"
            ))
            return self._build_result()
        
        lines = content.split('\n')
        
        # Validate based on format
        if self.format == SPICEFormat.HSPICE:
            self._validate_hspice(lines)
        elif self.format == SPICEFormat.NGSPICE:
            self._validate_ngspice(lines)
        elif self.format == SPICEFormat.SPECTRE:
            self._validate_spectre(lines)
        
        return self._build_result()
    
    def _build_result(self) -> SyntaxValidationResult:
        """Build validation result."""
        if self.strict:
            valid = len(self.errors) == 0 and len(self.warnings) == 0
        else:
            valid = len(self.errors) == 0
        
        return SyntaxValidationResult(
            valid=valid,
            format=self.format,
            errors=self.errors,
            warnings=self.warnings,
            info=self.info
        )
    
    def _validate_hspice(self, lines: List[str]) -> None:
        """Validate HSPICE syntax."""
        in_model = False
        in_subckt = False
        
        for i, line in enumerate(lines, start=1):
            line_stripped = line.strip()
            
            # Skip empty lines
            if not line_stripped:
                continue
            
            # Check comments
            if line_stripped.startswith('*') or line_stripped.startswith('$'):
                continue
            
            # Check line continuation (HSPICE uses +)
            if line_stripped.startswith('+'):
                if i == 1:
                    self.errors.append(SyntaxError(
                        severity=SyntaxSeverity.ERROR,
                        line_number=i,
                        line_content=line,
                        message="Continuation line at beginning of file",
                        suggestion="Remove leading '+' or add previous line"
                    ))
                continue
            
            # Check .MODEL statements
            if line_stripped.upper().startswith('.MODEL'):
                in_model = True
                self._check_model_statement(line, i, 'hspice')
            
            # Check .SUBCKT statements
            elif line_stripped.upper().startswith('.SUBCKT'):
                in_subckt = True
                self._check_subckt_statement(line, i, 'hspice')
            
            # Check .ENDS statements
            elif line_stripped.upper().startswith('.ENDS'):
                if not in_subckt:
                    self.warnings.append(SyntaxError(
                        severity=SyntaxSeverity.WARNING,
                        line_number=i,
                        line_content=line,
                        message=".ENDS without matching .SUBCKT"
                    ))
                in_subckt = False
            
            # Check .LIB statements
            elif line_stripped.upper().startswith('.LIB'):
                self._check_lib_statement(line, i, 'hspice')
            
            # Check .INCLUDE statements
            elif line_stripped.upper().startswith('.INCLUDE'):
                self._check_include_statement(line, i, 'hspice')
            
            # Check for invalid characters in HSPICE
            if any(ord(c) > 127 for c in line):
                self.warnings.append(SyntaxError(
                    severity=SyntaxSeverity.WARNING,
                    line_number=i,
                    line_content=line,
                    message="Non-ASCII characters detected",
                    suggestion="Use ASCII characters only for compatibility"
                ))
    
    def _validate_ngspice(self, lines: List[str]) -> None:
        """Validate ngspice syntax."""
        in_model = False
        in_subckt = False
        
        for i, line in enumerate(lines, start=1):
            line_stripped = line.strip()
            
            # Skip empty lines
            if not line_stripped:
                continue
            
            # Check comments
            if line_stripped.startswith('*'):
                continue
            
            # Check line continuation (ngspice uses +)
            if line_stripped.startswith('+'):
                if i == 1:
                    self.errors.append(SyntaxError(
                        severity=SyntaxSeverity.ERROR,
                        line_number=i,
                        line_content=line,
                        message="Continuation line at beginning of file"
                    ))
                continue
            
            # Check .model statements (case-insensitive)
            if line_stripped.upper().startswith('.MODEL'):
                in_model = True
                self._check_model_statement(line, i, 'ngspice')
            
            # Check .subckt statements
            elif line_stripped.upper().startswith('.SUBCKT'):
                in_subckt = True
                self._check_subckt_statement(line, i, 'ngspice')
            
            # Check .ends statements
            elif line_stripped.upper().startswith('.ENDS'):
                if not in_subckt:
                    self.warnings.append(SyntaxError(
                        severity=SyntaxSeverity.WARNING,
                        line_number=i,
                        line_content=line,
                        message=".ends without matching .subckt"
                    ))
                in_subckt = False
            
            # Check .lib statements
            elif line_stripped.upper().startswith('.LIB'):
                self._check_lib_statement(line, i, 'ngspice')
            
            # Check .include statements
            elif line_stripped.upper().startswith('.INCLUDE'):
                self._check_include_statement(line, i, 'ngspice')
    
    def _validate_spectre(self, lines: List[str]) -> None:
        """Validate Spectre syntax."""
        in_model = False
        in_subckt = False
        
        for i, line in enumerate(lines, start=1):
            line_stripped = line.strip()
            
            # Skip empty lines
            if not line_stripped:
                continue
            
            # Check comments (Spectre uses // or /*)
            if line_stripped.startswith('//') or line_stripped.startswith('/*'):
                continue
            
            # Check line continuation (Spectre uses \)
            if line.rstrip().endswith('\\'):
                continue
            
            # Check model statements
            if line_stripped.startswith('model'):
                in_model = True
                self._check_model_statement(line, i, 'spectre')
            
            # Check subckt statements
            elif line_stripped.startswith('subckt'):
                in_subckt = True
                self._check_subckt_statement(line, i, 'spectre')
            
            # Check ends statements
            elif line_stripped.startswith('ends'):
                if not in_subckt:
                    self.warnings.append(SyntaxError(
                        severity=SyntaxSeverity.WARNING,
                        line_number=i,
                        line_content=line,
                        message="ends without matching subckt"
                    ))
                in_subckt = False
            
            # Check include statements
            elif line_stripped.startswith('include'):
                self._check_include_statement(line, i, 'spectre')
    
    def _check_model_statement(self, line: str, line_num: int, format: str) -> None:
        """Check .MODEL statement syntax."""
        line_stripped = line.strip()
        
        if format in ['hspice', 'ngspice']:
            # .MODEL name type [parameters]
            parts = line_stripped.split(None, 2)
            if len(parts) < 3:
                self.errors.append(SyntaxError(
                    severity=SyntaxSeverity.ERROR,
                    line_number=line_num,
                    line_content=line,
                    message=".MODEL requires name and type",
                    suggestion=".MODEL <name> <type> [parameters]"
                ))
        else:  # spectre
            # model name type [parameters]
            parts = line_stripped.split(None, 2)
            if len(parts) < 3:
                self.errors.append(SyntaxError(
                    severity=SyntaxSeverity.ERROR,
                    line_number=line_num,
                    line_content=line,
                    message="model requires name and type",
                    suggestion="model <name> <type> [parameters]"
                ))
    
    def _check_subckt_statement(self, line: str, line_num: int, format: str) -> None:
        """Check .SUBCKT statement syntax."""
        line_stripped = line.strip()
        
        if format in ['hspice', 'ngspice']:
            # .SUBCKT name [nodes]
            parts = line_stripped.split(None, 1)
            if len(parts) < 2:
                self.errors.append(SyntaxError(
                    severity=SyntaxSeverity.ERROR,
                    line_number=line_num,
                    line_content=line,
                    message=".SUBCKT requires name",
                    suggestion=".SUBCKT <name> [nodes]"
                ))
        else:  # spectre
            # subckt name [nodes]
            parts = line_stripped.split(None, 1)
            if len(parts) < 2:
                self.errors.append(SyntaxError(
                    severity=SyntaxSeverity.ERROR,
                    line_number=line_num,
                    line_content=line,
                    message="subckt requires name",
                    suggestion="subckt <name> [nodes]"
                ))
    
    def _check_lib_statement(self, line: str, line_num: int, format: str) -> None:
        """Check .LIB statement syntax."""
        line_stripped = line.strip()
        
        # .LIB 'filename' section
        # Check for quotes around filename
        if "'" not in line and '"' not in line:
            self.warnings.append(SyntaxError(
                severity=SyntaxSeverity.WARNING,
                line_number=line_num,
                line_content=line,
                message="Library filename should be quoted",
                suggestion=".LIB 'filename' [section]"
            ))
    
    def _check_include_statement(self, line: str, line_num: int, format: str) -> None:
        """Check .INCLUDE statement syntax."""
        line_stripped = line.strip()
        
        if format in ['hspice', 'ngspice']:
            # .INCLUDE 'filename' or .INCLUDE "filename"
            if "'" not in line and '"' not in line:
                self.warnings.append(SyntaxError(
                    severity=SyntaxSeverity.WARNING,
                    line_number=line_num,
                    line_content=line,
                    message="Include filename should be quoted",
                    suggestion=".INCLUDE 'filename'"
                ))
        else:  # spectre
            # include "filename"
            if '"' not in line:
                self.warnings.append(SyntaxError(
                    severity=SyntaxSeverity.WARNING,
                    line_number=line_num,
                    line_content=line,
                    message="Include filename should be quoted",
                    suggestion='include "filename"'
                ))
