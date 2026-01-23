# Validation Quick Start Guide

This guide shows how to use the Phase 5 validation system.

## Installation

No additional installation needed - validators are part of the main package:

```python
from src.validation import (
    IRValidator,
    SyntaxValidator,
    ParameterValidator,
    TranslationValidator,
    SPICEFormat
)
```

## Basic Usage

### 1. IR Validation

Validate ModelIR objects before translation:

```python
from src.validation import IRValidator

# Create validator
validator = IRValidator(strict=False)

# Validate models
result = validator.validate(model_list)

# Check results
if result.valid:
    print("✓ IR validation passed")
    print(f"  {result.warning_count} warnings")
else:
    print("✗ IR validation failed")
    for error in result.errors:
        print(f"  {error}")
```

### 2. Syntax Validation

Validate generated SPICE netlist syntax:

```python
from src.validation import SyntaxValidator, SPICEFormat

# Create validator for specific format
validator = SyntaxValidator(SPICEFormat.HSPICE)

# Validate netlist content
with open("output.sp", "r") as f:
    content = f.read()

result = validator.validate(content)

# Check results
if not result.valid:
    for error in result.errors:
        print(f"Line {error.line_number}: {error.message}")
        print(f"  {error.line_content}")
        if error.suggestion:
            print(f"  Suggestion: {error.suggestion}")
```

### 3. Parameter Validation

Validate parameter values and equivalence:

```python
from src.validation import ParameterValidator

# Single model validation
validator = ParameterValidator(tolerance=0.01)  # 1% tolerance
result = validator.validate(model)

# Check for parameter issues
for warning in result.warnings:
    print(f"⚠ {warning}")

# Equivalence validation (compare source vs target)
result = validator.validate_equivalence(
    source=source_model,
    target=target_model
)

if result.valid:
    print("✓ Parameters match within tolerance")
else:
    print("✗ Parameter differences detected:")
    for issue in result.warnings:
        print(f"  {issue}")
```

### 4. Full Translation Validation

Validate complete translation workflow:

```python
from src.validation import TranslationValidator

# Create validator
validator = TranslationValidator(strict=False, tolerance=0.01)

# Validate translation
result = validator.validate_translation(
    source_ir=source_models,
    target_ir=target_models,
    target_content=generated_netlist,
    source_format="hspice",
    target_format="ngspice"
)

# Check results
print(result)  # ✓ Translation hspice→ngspice valid (2 warnings)
print(f"Errors: {result.total_errors}")
print(f"Warnings: {result.total_warnings}")

# Generate detailed report
report = validator.generate_report(result)
print(report)

# Save report to file
validator.generate_report(result, output_path="validation_report.txt")
```

## Advanced Usage

### Round-Trip Validation

Test that `source → target → source` produces identical results:

```python
from src.parsers import HspiceParser, NgspiceParser
from src.writers import NgspiceWriter, HspiceWriter
from src.validation import TranslationValidator

# 1. Parse source
hspice_parser = HspiceParser()
source_models = hspice_parser.parse_file("input.sp")

# 2. Translate to ngspice
ngspice_writer = NgspiceWriter()
ngspice_content = ngspice_writer.write_models(source_models, "temp.sp")

# 3. Parse ngspice back
ngspice_parser = NgspiceParser()
ngspice_models = ngspice_parser.parse_file("temp.sp")

# 4. Translate back to hspice
hspice_writer = HspiceWriter()
final_content = hspice_writer.write_models(ngspice_models, "final.sp")

# 5. Parse final result
final_models = hspice_parser.parse_file("final.sp")

# 6. Validate round-trip
validator = TranslationValidator()
result = validator.validate_round_trip(
    source_models=source_models,
    final_models=final_models
)

if result.valid:
    print("✓ Round-trip successful")
else:
    print("✗ Round-trip produced differences:")
    for diff in result.differences:
        print(f"  {diff}")
```

### Strict Mode

Use strict mode in production to catch all issues:

```python
# Strict mode: warnings are treated as errors
validator = IRValidator(strict=True)
result = validator.validate(models)

if not result.valid:
    print("Validation failed (strict mode)")
    print(f"Errors: {result.error_count}")
    print(f"Warnings: {result.warning_count}")
    
    # Both errors and warnings will cause validation failure
    all_issues = result.errors + result.warnings
    for issue in all_issues:
        print(f"  {issue}")
```

### Custom Tolerance

Adjust parameter comparison tolerance:

```python
# Tight tolerance (0.1%)
validator = ParameterValidator(tolerance=0.001)

# Loose tolerance (5%)
validator = ParameterValidator(tolerance=0.05)

# Validate equivalence
result = validator.validate_equivalence(source, target)
```

### Selective Validation

Enable/disable specific validators:

```python
validator = TranslationValidator()

result = validator.validate_translation(
    source_ir=source,
    target_ir=target,
    target_content=content,
    source_format="hspice",
    target_format="ngspice",
    validate_ir=True,        # Enable IR validation
    validate_syntax=True,    # Enable syntax validation
    validate_parameters=False  # Skip parameter validation
)
```

## Integration Examples

### Pre-Translation Validation

```python
# Validate IR before translation
ir_validator = IRValidator(strict=True)
ir_result = ir_validator.validate(models)

if not ir_result.valid:
    print("Cannot translate - IR validation failed")
    sys.exit(1)

# Proceed with translation
writer = NgspiceWriter()
writer.write_models(models, "output.sp")
```

### Post-Translation Validation

```python
# After translation, validate output
syntax_validator = SyntaxValidator(SPICEFormat.NGSPICE)

with open("output.sp", "r") as f:
    content = f.read()

result = syntax_validator.validate(content)

if not result.valid:
    print("Generated netlist has syntax errors:")
    for error in result.errors:
        print(f"  Line {error.line_number}: {error.message}")
```

### Continuous Validation

```python
def translate_with_validation(input_file, output_file, 
                              source_fmt, target_fmt):
    """Translate with comprehensive validation."""
    
    # Parse
    parser = get_parser(source_fmt)
    models = parser.parse_file(input_file)
    
    # Validate IR
    ir_validator = IRValidator(strict=False)
    ir_result = ir_validator.validate(models)
    if not ir_result.valid:
        raise ValueError(f"IR validation failed: {ir_result}")
    
    # Translate
    writer = get_writer(target_fmt)
    content = writer.write_models(models, output_file)
    
    # Validate syntax
    syntax_validator = SyntaxValidator(SPICEFormat(target_fmt))
    syntax_result = syntax_validator.validate(content)
    if not syntax_result.valid:
        raise ValueError(f"Syntax validation failed: {syntax_result}")
    
    # Full validation
    trans_validator = TranslationValidator()
    result = trans_validator.validate_translation(
        source_ir=models,
        target_ir=models,
        target_content=content,
        source_format=source_fmt,
        target_format=target_fmt
    )
    
    return result

# Use it
result = translate_with_validation(
    "input.sp", "output.sp",
    "hspice", "ngspice"
)
print(result.get_summary())
```

## Common Patterns

### Pattern 1: Fail Fast

```python
validators = [
    IRValidator(strict=True),
    SyntaxValidator(SPICEFormat.HSPICE),
    ParameterValidator(tolerance=0.01)
]

for validator in validators:
    result = validator.validate(...)
    if not result.valid:
        print(f"Validation failed: {result}")
        break
```

### Pattern 2: Collect All Issues

```python
all_errors = []
all_warnings = []

# Run all validators
ir_result = ir_validator.validate(models)
syntax_result = syntax_validator.validate(content)
param_result = param_validator.validate(model)

# Collect issues
all_errors.extend(ir_result.errors)
all_errors.extend(syntax_result.errors)
all_errors.extend(param_result.errors)

all_warnings.extend(ir_result.warnings)
all_warnings.extend(syntax_result.warnings)
all_warnings.extend(param_result.warnings)

# Report all
print(f"Total issues: {len(all_errors)} errors, {len(all_warnings)} warnings")
```

### Pattern 3: Automated Reports

```python
def validate_and_report(models, content, format):
    """Validate and generate report automatically."""
    
    validator = TranslationValidator()
    result = validator.validate_translation(
        source_ir=models,
        target_ir=models,
        target_content=content,
        source_format=format,
        target_format=format
    )
    
    # Auto-generate report file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"validation_report_{timestamp}.txt"
    
    validator.generate_report(result, output_path=report_file)
    
    return result, report_file
```

## Troubleshooting

### Issue: Too Many Warnings

**Solution**: Adjust validator settings or use selective validation

```python
# Less strict
validator = ParameterValidator(tolerance=0.05)  # 5% tolerance

# Skip optional validations
result = trans_validator.validate_translation(
    ...,
    validate_parameters=False  # Skip if too noisy
)
```

### Issue: Need More Detail

**Solution**: Use detailed error reporting

```python
result = validator.validate(models)

for error in result.errors:
    print(f"Error: {error.message}")
    if error.field:
        print(f"  Field: {error.field}")
    if error.model_name:
        print(f"  Model: {error.model_name}")
    if error.suggestion:
        print(f"  Fix: {error.suggestion}")
```

### Issue: Validation Too Slow

**Solution**: Use selective validation or optimize

```python
# Skip expensive validations for large files
if file_size > 10_000_000:  # 10 MB
    validate_syntax = False
else:
    validate_syntax = True
```

## Best Practices

1. **Use strict mode in production**
2. **Validate early** (before translation)
3. **Validate often** (after each stage)
4. **Save validation reports** for debugging
5. **Adjust tolerance** based on use case
6. **Review warnings** even if validation passes

## See Also

- [PHASE5_VALIDATION.md](PHASE5_VALIDATION.md) - Complete documentation
- [PHASE5_SUMMARY.md](PHASE5_SUMMARY.md) - Implementation summary
- API documentation in source code docstrings
