"""
Enhanced expression parser for complex SPICE parameter values.

This module handles sophisticated parameter expressions including:
- Mathematical operations: +, -, *, /, ** (power)
- Scientific notation: -2e-08, 1.5E+10
- Parameter references: dlxn, toxe_nom
- Functions: sqrt(), log(), exp(), abs()
- Conditional expressions: {condition ? value1 : value2}
- Unit conversions and scaling factors

Author: SPICE Translator Enhanced Parser v2.0
"""

import re
import math
import ast
import operator
from typing import Any, Dict, List, Union, Optional, Callable
from dataclasses import dataclass
from enum import Enum


class ExpressionType(Enum):
    """Types of parameter expressions that can be parsed."""
    SIMPLE_VALUE = "simple_value"           # 1.5, -2.3e-8
    MATHEMATICAL = "mathematical"           # 2*tox + 1e-9
    PARAMETER_REF = "parameter_reference"   # dlxn, toxe_nom
    CONDITIONAL = "conditional"             # {vth0 > 0 ? 1.2 : 0.8}
    FUNCTION_CALL = "function_call"         # sqrt(toxe), log(w*l)
    COMPLEX_EXPR = "complex_expression"     # Multiple operations


@dataclass
class ParsedExpression:
    """Container for parsed expression results."""
    original: str
    expression_type: ExpressionType
    value: Any
    dependencies: List[str]  # Parameter names this expression depends on
    success: bool
    error_message: Optional[str] = None
    confidence: float = 1.0  # Confidence in parse accuracy (0.0-1.0)


class EnhancedExpressionParser:
    """Advanced parser for complex SPICE parameter expressions."""
    
    # Supported mathematical functions
    MATH_FUNCTIONS = {
        'sqrt': math.sqrt,
        'log': math.log,
        'ln': math.log,
        'log10': math.log10,
        'exp': math.exp,
        'abs': abs,
        'sin': math.sin,
        'cos': math.cos,
        'tan': math.tan,
        'pow': pow,
        'min': min,
        'max': max,
    }
    
    # Mathematical operators
    OPERATORS = {
        '+': operator.add,
        '-': operator.sub,
        '*': operator.mul,
        '/': operator.truediv,
        '**': operator.pow,
        '^': operator.pow,  # Alternative power notation
    }
    
    def __init__(self, parameter_context: Optional[Dict[str, Any]] = None):
        """Initialize the expression parser.
        
        Args:
            parameter_context: Dictionary of parameter values for substitution
        """
        self.parameter_context = parameter_context or {}
        self.parse_cache = {}  # Cache for repeated expressions
        
    def parse_expression(self, expression: str) -> ParsedExpression:
        """Parse a parameter expression and return structured result.
        
        Args:
            expression: The parameter expression to parse
            
        Returns:
            ParsedExpression containing parsed results and metadata
        """
        if not expression or not isinstance(expression, str):
            return ParsedExpression(
                original=str(expression),
                expression_type=ExpressionType.SIMPLE_VALUE,
                value=expression,
                dependencies=[],
                success=bool(expression),
                error_message="Empty or invalid expression" if not expression else None
            )
        
        # Check cache first
        if expression in self.parse_cache:
            return self.parse_cache[expression]
            
        expression = expression.strip()
        original = expression
        
        try:
            # Determine expression type and parse accordingly
            expr_type = self._classify_expression(expression)
            
            if expr_type == ExpressionType.SIMPLE_VALUE:
                result = self._parse_simple_value(expression)
            elif expr_type == ExpressionType.PARAMETER_REF:
                result = self._parse_parameter_reference(expression)
            elif expr_type == ExpressionType.MATHEMATICAL:
                result = self._parse_mathematical_expression(expression)
            elif expr_type == ExpressionType.CONDITIONAL:
                result = self._parse_conditional_expression(expression)
            elif expr_type == ExpressionType.FUNCTION_CALL:
                result = self._parse_function_call(expression)
            else:  # COMPLEX_EXPR
                result = self._parse_complex_expression(expression)
                
            result.original = original
            result.expression_type = expr_type
            
            # Cache successful parses
            if result.success:
                self.parse_cache[expression] = result
                
            return result
            
        except Exception as e:
            return ParsedExpression(
                original=original,
                expression_type=ExpressionType.SIMPLE_VALUE,
                value=expression,  # Fall back to original string
                dependencies=[],
                success=False,
                error_message=f"Parse error: {str(e)}",
                confidence=0.0
            )
    
    def _classify_expression(self, expression: str) -> ExpressionType:
        """Classify the type of expression for appropriate parsing."""
        expression = expression.strip()
        
        # Check for conditional expressions: {condition ? value1 : value2}
        if re.search(r'\{[^}]*\?[^}]*:[^}]*\}', expression):
            return ExpressionType.CONDITIONAL
            
        # Check for function calls: func(...)
        if re.search(r'\b[a-zA-Z_]\w*\s*\(', expression):
            return ExpressionType.FUNCTION_CALL
            
        # Check for mathematical operators
        if re.search(r'[+\-*/%^]', expression) and not self._is_simple_scientific_notation(expression):
            return ExpressionType.MATHEMATICAL
            
        # Check if it's a parameter reference (contains letters)
        if re.search(r'[a-zA-Z_]', expression) and not re.search(r'^-?\d*\.?\d+[eE][+-]?\d+$', expression):
            return ExpressionType.PARAMETER_REF
            
        # Default to simple value
        return ExpressionType.SIMPLE_VALUE
    
    def _is_simple_scientific_notation(self, expression: str) -> bool:
        """Check if expression is simple scientific notation like -2.3e-8."""
        pattern = r'^[+-]?\d*\.?\d+[eE][+-]?\d+$'
        return bool(re.match(pattern, expression.replace(' ', '')))
    
    def _parse_simple_value(self, expression: str) -> ParsedExpression:
        """Parse simple numeric values including scientific notation."""
        try:
            # Handle scientific notation and regular numbers
            if re.search(r'[eE]', expression):
                value = float(expression)
            elif '.' in expression:
                value = float(expression)
            else:
                # Try integer first, then float
                try:
                    value = int(expression)
                except ValueError:
                    value = float(expression)
                    
            return ParsedExpression(
                original=expression,
                expression_type=ExpressionType.SIMPLE_VALUE,
                value=value,
                dependencies=[],
                success=True,
                confidence=1.0
            )
            
        except ValueError:
            # If numeric parsing fails, keep as string
            return ParsedExpression(
                original=expression,
                expression_type=ExpressionType.SIMPLE_VALUE,
                value=expression.strip('"\''),  # Remove quotes if present
                dependencies=[],
                success=True,
                confidence=0.8  # String values have lower confidence
            )
    
    def _parse_parameter_reference(self, expression: str) -> ParsedExpression:
        """Parse parameter references like 'dlxn' or 'toxe_nom'."""
        # Clean parameter name
        param_name = re.sub(r'[^\w]', '', expression)
        
        # Check if parameter exists in context
        if param_name in self.parameter_context:
            value = self.parameter_context[param_name]
            confidence = 1.0
        else:
            # Keep as symbolic reference
            value = param_name
            confidence = 0.6  # Lower confidence for unresolved references
            
        return ParsedExpression(
            original=expression,
            expression_type=ExpressionType.PARAMETER_REF,
            value=value,
            dependencies=[param_name],
            success=True,
            confidence=confidence
        )
    
    def _parse_mathematical_expression(self, expression: str) -> ParsedExpression:
        """Parse mathematical expressions like '2*tox + 1e-9'."""
        try:
            # Extract parameter names for dependencies (excluding scientific notation)
            # First, temporarily replace scientific notation to avoid false positives
            temp_expr = expression
            sci_pattern = r'[-+]?\d*\.?\d+[eE][-+]?\d+'
            sci_matches = re.findall(sci_pattern, expression)
            
            # Replace scientific notation with placeholders
            for i, match in enumerate(sci_matches):
                temp_expr = temp_expr.replace(match, f'__SCI_{i}__', 1)
            
            # Now extract parameter names (excluding function names and placeholders)
            dependencies = re.findall(r'[a-zA-Z_]\w*', temp_expr)
            dependencies = [dep for dep in dependencies if not dep.startswith('__SCI_') and dep not in self.MATH_FUNCTIONS]
            
            # Try to evaluate if all parameters are available
            eval_expr = expression
            available_params = set(self.parameter_context.keys())
            missing_params = set(dependencies) - available_params
            
            if not missing_params:
                # All parameters available - try evaluation
                try:
                    # Replace parameter names with values
                    for param in dependencies:
                        if param in self.MATH_FUNCTIONS:
                            continue  # Don't replace function names
                        value = self.parameter_context[param]
                        eval_expr = re.sub(rf'\b{param}\b', str(value), eval_expr)
                    
                    # Evaluate safely
                    result = self._safe_eval(eval_expr)
                    
                    return ParsedExpression(
                        original=expression,
                        expression_type=ExpressionType.MATHEMATICAL,
                        value=result,
                        dependencies=dependencies,
                        success=True,
                        confidence=1.0
                    )
                    
                except:
                    pass  # Fall through to symbolic representation
            
            # Return symbolic representation if evaluation fails
            return ParsedExpression(
                original=expression,
                expression_type=ExpressionType.MATHEMATICAL,
                value=expression,  # Keep as symbolic
                dependencies=dependencies,
                success=True,
                confidence=0.7
            )
            
        except Exception as e:
            return ParsedExpression(
                original=expression,
                expression_type=ExpressionType.MATHEMATICAL,
                value=expression,
                dependencies=[],
                success=False,
                error_message=str(e),
                confidence=0.0
            )
    
    def _parse_conditional_expression(self, expression: str) -> ParsedExpression:
        """Parse conditional expressions like '{vth0 > 0 ? 1.2 : 0.8}'."""
        # Extract conditional pattern
        match = re.search(r'\{([^}]*)\?([^}]*):([^}]*)\}', expression)
        
        if not match:
            return ParsedExpression(
                original=expression,
                expression_type=ExpressionType.CONDITIONAL,
                value=expression,
                dependencies=[],
                success=False,
                error_message="Invalid conditional syntax"
            )
        
        condition, true_value, false_value = match.groups()
        condition = condition.strip()
        true_value = true_value.strip()
        false_value = false_value.strip()
        
        # Extract dependencies from all parts
        cond_deps = re.findall(r'[a-zA-Z_]\w*', condition)
        true_deps = re.findall(r'[a-zA-Z_]\w*', true_value)
        false_deps = re.findall(r'[a-zA-Z_]\w*', false_value)
        dependencies = cond_deps + true_deps + false_deps
        dependencies = [d for d in dependencies if d not in ['true', 'false']]  # Remove boolean keywords
        
        return ParsedExpression(
            original=expression,
            expression_type=ExpressionType.CONDITIONAL,
            value=f"conditional({condition}, {true_value}, {false_value})",
            dependencies=dependencies,
            success=True,
            confidence=0.8  # Conditionals need special handling
        )
    
    def _parse_function_call(self, expression: str) -> ParsedExpression:
        """Parse function calls like 'sqrt(toxe)' or 'log(w*l)'."""
        # Extract function name and arguments
        match = re.match(r'(\w+)\s*\(([^)]*)\)', expression)
        
        if not match:
            return ParsedExpression(
                original=expression,
                expression_type=ExpressionType.FUNCTION_CALL,
                value=expression,
                dependencies=[],
                success=False,
                error_message="Invalid function syntax"
            )
        
        func_name, args = match.groups()
        args = args.strip()
        
        # Check for empty arguments
        if not args:
            return ParsedExpression(
                original=expression,
                expression_type=ExpressionType.FUNCTION_CALL,
                value=expression,
                dependencies=[],
                success=False,
                error_message="Function requires arguments"
            )
        
        # Extract dependencies from arguments
        dependencies = re.findall(r'[a-zA-Z_]\w*', args)
        
        # Check if function is supported
        if func_name not in self.MATH_FUNCTIONS:
            return ParsedExpression(
                original=expression,
                expression_type=ExpressionType.FUNCTION_CALL,
                value=expression,
                dependencies=dependencies,
                success=True,
                confidence=0.5  # Unsupported function
            )
        
        # Try to evaluate if possible
        try:
            if not dependencies or all(dep in self.parameter_context for dep in dependencies):
                # Substitute parameters and evaluate
                eval_args = args
                for param in dependencies:
                    if param in self.parameter_context:
                        eval_args = re.sub(rf'\b{param}\b', str(self.parameter_context[param]), eval_args)
                
                arg_value = self._safe_eval(eval_args)
                result = self.MATH_FUNCTIONS[func_name](arg_value)
                
                return ParsedExpression(
                    original=expression,
                    expression_type=ExpressionType.FUNCTION_CALL,
                    value=result,
                    dependencies=dependencies,
                    success=True,
                    confidence=1.0
                )
        except:
            pass
        
        # Return symbolic representation
        return ParsedExpression(
            original=expression,
            expression_type=ExpressionType.FUNCTION_CALL,
            value=expression,
            dependencies=dependencies,
            success=True,
            confidence=0.8
        )
    
    def _parse_complex_expression(self, expression: str) -> ParsedExpression:
        """Parse complex expressions with multiple operations."""
        # For now, treat as mathematical expression
        return self._parse_mathematical_expression(expression)
    
    def _safe_eval(self, expression: str) -> float:
        """Safely evaluate mathematical expressions."""
        # Replace operators
        expression = expression.replace('^', '**')
        
        # Create safe evaluation environment
        safe_dict = {
            "__builtins__": {},
            **self.MATH_FUNCTIONS
        }
        
        try:
            # Use ast.literal_eval for simple expressions
            return ast.literal_eval(expression)
        except:
            # Fall back to eval with restricted environment
            return eval(expression, {"__builtins__": {}}, safe_dict)


def parse_parameter_value(value: str, context: Optional[Dict[str, Any]] = None) -> ParsedExpression:
    """Convenience function to parse a single parameter value.
    
    Args:
        value: Parameter value expression to parse
        context: Optional parameter context for substitutions
        
    Returns:
        ParsedExpression with parsed results
    """
    parser = EnhancedExpressionParser(context)
    return parser.parse_expression(value)


# Example usage and testing
if __name__ == "__main__":
    # Test cases for the enhanced expression parser
    test_expressions = [
        "1.5",
        "-2.3e-8",
        "dlxn",
        "2*tox + 1e-9", 
        "-2e-08 + dlxn",
        "sqrt(toxe)",
        "{vth0 > 0 ? 1.2 : 0.8}",
        "log(w*l/1e-12)"
    ]
    
    # Test context
    context = {
        'tox': 2.1e-9,
        'dlxn': 1.5e-8,
        'toxe': 2.0e-9,
        'vth0': 0.4,
        'w': 1e-6,
        'l': 0.18e-6
    }
    
    parser = EnhancedExpressionParser(context)
    
    print("Enhanced Expression Parser Test Results:")
    print("=" * 50)
    
    for expr in test_expressions:
        result = parser.parse_expression(expr)
        print(f"\nExpression: {expr}")
        print(f"Type: {result.expression_type.value}")
        print(f"Value: {result.value}")
        print(f"Dependencies: {result.dependencies}")
        print(f"Success: {result.success}")
        print(f"Confidence: {result.confidence:.2f}")
        if result.error_message:
            print(f"Error: {result.error_message}")