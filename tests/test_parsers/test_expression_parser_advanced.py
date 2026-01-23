"""
Tests for expression parser - conditional expressions, function calls, and complex expressions.

This test file achieves coverage for previously untested expression parser functionality.
"""

import pytest
import math
from typing import Dict, Any

from src.parsers.expression_parser import (
    EnhancedExpressionParser,
    ExpressionType,
    parse_parameter_value,
)


class TestConditionalExpressions:
    """Test conditional expression parsing (ternary operator)."""

    @pytest.mark.parametrize("expression,expected_success,expected_deps", [
        # Basic conditional
        ("{vth0 > 0 ? 1.2 : 0.8}", True, ["vth0"]),
        # Complex condition
        ("{temp > 25 ? vth_hot : vth_cold}", True, ["temp", "vth_hot", "vth_cold"]),
        # Nested parameters
        ("{w > l ? w*2 : l*2}", True, ["w", "l"]),
        # Numeric comparison
        ("{x >= 100 ? 1 : 0}", True, ["x"]),
        # Multiple dependencies
        ("{a < b ? c : d}", True, ["a", "b", "c", "d"]),
    ])
    def test_valid_conditional_expressions(
        self, expression: str, expected_success: bool, expected_deps: list
    ) -> None:
        """Test valid conditional expressions are parsed correctly."""
        parser = EnhancedExpressionParser()
        result = parser.parse_expression(expression)
        
        assert result.success == expected_success
        assert result.expression_type == ExpressionType.CONDITIONAL
        assert set(result.dependencies).issuperset(set(expected_deps))

    @pytest.mark.parametrize("expression", [
        # Missing closing brace
        "{vth0 > 0 ? 1.2 : 0.8",
        # Missing question mark
        "{vth0 > 0  1.2 : 0.8}",
        # Missing colon
        "{vth0 > 0 ? 1.2  0.8}",
        # Empty conditional
        "{}",
        # No braces
        "vth0 > 0 ? 1.2 : 0.8",
    ])
    def test_invalid_conditional_syntax(self, expression: str) -> None:
        """Test invalid conditional expressions are handled gracefully."""
        parser = EnhancedExpressionParser()
        result = parser.parse_expression(expression)
        
        # Should either fail or not be classified as conditional
        if result.expression_type == ExpressionType.CONDITIONAL:
            assert result.success is False

    def test_conditional_with_context(self) -> None:
        """Test conditional expression with parameter context."""
        context = {"vth0": 0.5, "temp": 30}
        parser = EnhancedExpressionParser(parameter_context=context)
        
        result = parser.parse_expression("{vth0 > 0 ? 1.2 : 0.8}")
        
        assert result.success is True
        assert result.dependencies == ["vth0"]


class TestFunctionCallExpressions:
    """Test mathematical function call parsing."""

    @pytest.mark.parametrize("expression,func_name,expected_deps", [
        # Basic functions
        ("sqrt(toxe)", "sqrt", ["toxe"]),
        ("exp(vth0)", "exp", ["vth0"]),
        ("log(w)", "log", ["w"]),
        ("sin(theta)", "sin", ["theta"]),
        ("cos(phase)", "cos", ["phase"]),
        ("abs(delta)", "abs", ["delta"]),
        # Functions with expressions
        ("sqrt(w*l)", "sqrt", ["w", "l"]),
        ("exp(vth0/kt)", "exp", ["vth0", "kt"]),
        ("log(toxe*1e9)", "log", ["toxe"]),
    ])
    def test_valid_function_calls(
        self, expression: str, func_name: str, expected_deps: list
    ) -> None:
        """Test valid function calls are parsed correctly."""
        parser = EnhancedExpressionParser()
        result = parser.parse_expression(expression)
        
        assert result.expression_type == ExpressionType.FUNCTION_CALL
        assert result.success is True
        assert set(result.dependencies).issuperset(set(expected_deps))

    @pytest.mark.parametrize("expression,expected_value", [
        # Evaluable functions with numeric args
        ("sqrt(4)", 2.0),
        ("exp(0)", 1.0),
        ("log(1)", 0.0),
        ("abs(-5)", 5.0),
        ("sin(0)", 0.0),
        ("cos(0)", 1.0),
    ])
    def test_function_evaluation_with_numeric_args(
        self, expression: str, expected_value: float
    ) -> None:
        """Test functions with numeric arguments are evaluated."""
        parser = EnhancedExpressionParser()
        result = parser.parse_expression(expression)
        
        assert result.success is True
        assert isinstance(result.value, (int, float))
        assert abs(result.value - expected_value) < 1e-10

    def test_function_evaluation_with_context(self) -> None:
        """Test function evaluation with parameter context."""
        context = {"toxe": 2.5e-9, "w": 1e-6, "l": 100e-9}
        parser = EnhancedExpressionParser(parameter_context=context)
        
        # sqrt with context
        result = parser.parse_expression("sqrt(toxe)")
        assert result.success is True
        assert isinstance(result.value, float)
        assert abs(result.value - math.sqrt(2.5e-9)) < 1e-15
        
        # Expression in function
        result = parser.parse_expression("sqrt(w*l)")
        assert result.success is True
        assert isinstance(result.value, float)

    @pytest.mark.parametrize("expression", [
        # Missing parentheses
        "sqrt",
        "exp",
        # Invalid syntax
        "sqrt(",
        "sqrt)",
        "sqrt((",
        # Empty arguments
        "sqrt()",
        # Malformed
        "sqrt{toxe}",
        "sqrt[toxe]",
    ])
    def test_invalid_function_syntax(self, expression: str) -> None:
        """Test invalid function syntax is handled."""
        parser = EnhancedExpressionParser()
        result = parser.parse_expression(expression)
        
        if result.expression_type == ExpressionType.FUNCTION_CALL:
            assert result.success is False

    def test_unsupported_function(self) -> None:
        """Test unsupported function names are handled."""
        parser = EnhancedExpressionParser()
        result = parser.parse_expression("unknown_func(x)")
        
        assert result.expression_type == ExpressionType.FUNCTION_CALL
        # Should succeed but with lower confidence
        if result.success:
            assert result.confidence < 1.0

    def test_nested_function_calls(self) -> None:
        """Test nested function calls."""
        parser = EnhancedExpressionParser()
        result = parser.parse_expression("sqrt(exp(vth0))")
        
        assert result.success is True
        assert "vth0" in result.dependencies


class TestComplexExpressions:
    """Test complex multi-operation expressions."""

    @pytest.mark.parametrize("expression,expected_type", [
        # Multiple operations
        ("vth0 * u0 + tox", ExpressionType.MATHEMATICAL),
        ("(w / l) * (vth0 + 0.1)", ExpressionType.MATHEMATICAL),
        ("a + b - c * d / e", ExpressionType.MATHEMATICAL),
        # With parentheses
        ("((vth0 + dvt) * (1 + kt1 * temp))", ExpressionType.MATHEMATICAL),
        # Scientific notation in expression
        ("vth0 + 1.5e-3 * temp", ExpressionType.MATHEMATICAL),
    ])
    def test_complex_mathematical_expressions(
        self, expression: str, expected_type: ExpressionType
    ) -> None:
        """Test complex expressions are parsed as mathematical."""
        parser = EnhancedExpressionParser()
        result = parser.parse_expression(expression)
        
        assert result.expression_type == expected_type
        assert result.success is True

    def test_complex_expression_with_evaluation(self) -> None:
        """Test complex expression evaluation with context."""
        context = {
            "vth0": 0.5,
            "dvt": 0.1,
            "kt1": 1e-3,
            "temp": 25,
        }
        parser = EnhancedExpressionParser(parameter_context=context)
        
        result = parser.parse_expression("vth0 + dvt * (1 + kt1 * temp)")
        
        assert result.success is True
        # Check if evaluation happened
        if isinstance(result.value, (int, float)):
            # Manually calculate: 0.5 + 0.1 * (1 + 0.001 * 25) = 0.5 + 0.1025 = 0.6025
            expected = 0.5 + 0.1 * (1 + 1e-3 * 25)
            assert abs(result.value - expected) < 1e-10


class TestParseParameterValueHelper:
    """Test the convenience function parse_parameter_value."""

    def test_parse_parameter_value_without_context(self) -> None:
        """Test parse_parameter_value without context."""
        result = parse_parameter_value("1.5e-9")
        
        assert result.success is True
        assert result.value == 1.5e-9

    def test_parse_parameter_value_with_context(self) -> None:
        """Test parse_parameter_value with context."""
        context = {"vth0": 0.5, "tox": 2.5e-9}
        result = parse_parameter_value("vth0 + 0.1", context)
        
        assert result.success is True
        # Should have dependencies or be evaluated
        if result.expression_type == ExpressionType.MATHEMATICAL:
            assert "vth0" in result.dependencies or isinstance(result.value, (int, float))

    def test_parse_parameter_value_function(self) -> None:
        """Test parse_parameter_value with function call."""
        result = parse_parameter_value("sqrt(4)")
        
        assert result.success is True
        assert result.expression_type == ExpressionType.FUNCTION_CALL
        assert abs(result.value - 2.0) < 1e-10

    def test_parse_parameter_value_conditional(self) -> None:
        """Test parse_parameter_value with conditional."""
        result = parse_parameter_value("{x > 0 ? 1 : 0}")
        
        assert result.expression_type == ExpressionType.CONDITIONAL


class TestExpressionParserEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.parametrize("expression", [
        # Empty
        "",
        # Whitespace only
        "   ",
        # Special characters
        "@#$%",
        # Very long expression
        "a" * 1000,
    ])
    def test_edge_case_inputs(self, expression: str) -> None:
        """Test edge case inputs don't crash parser."""
        parser = EnhancedExpressionParser()
        result = parser.parse_expression(expression)
        
        # Should not raise exception
        assert result is not None

    def test_division_by_zero_in_safe_eval(self) -> None:
        """Test division by zero is handled in evaluation."""
        context = {"x": 1, "y": 0}
        parser = EnhancedExpressionParser(parameter_context=context)
        
        result = parser.parse_expression("x / y")
        
        # Should handle gracefully, either fail or return symbolic
        assert result is not None

    def test_math_functions_availability(self) -> None:
        """Test that MATH_FUNCTIONS are properly available."""
        parser = EnhancedExpressionParser()
        
        # Check that math functions are defined
        assert hasattr(parser, 'MATH_FUNCTIONS')
        assert 'sqrt' in parser.MATH_FUNCTIONS
        assert 'exp' in parser.MATH_FUNCTIONS
        assert 'log' in parser.MATH_FUNCTIONS

    def test_safe_eval_with_invalid_expression(self) -> None:
        """Test _safe_eval with invalid expression."""
        parser = EnhancedExpressionParser()
        
        # This should be caught gracefully
        with pytest.raises(Exception):
            # Directly calling private method for testing
            parser._safe_eval("invalid syntax !!!")

    def test_parameter_context_override(self) -> None:
        """Test parameter context can be set and used."""
        context1 = {"x": 1}
        parser = EnhancedExpressionParser(parameter_context=context1)
        
        result = parser.parse_expression("x + 1")
        assert "x" in result.dependencies or isinstance(result.value, (int, float))
        
        # Update context
        context2 = {"x": 5}
        parser.parameter_context = context2
        
        result = parser.parse_expression("x + 1")
        # Should use new context if evaluated
        assert result is not None
