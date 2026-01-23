# SPICE Translator IR Implementation - File Export Guide

**Version:** 2.0  
**Date:** January 4, 2026  
**Purpose:** Guide for migrating files from current project to new IR-based architecture

---

## Quick Reference: What to Copy

### ✅ **Copy Directly (No Changes Needed)**

These files work as-is in the new architecture:

```bash
# From current project → New project

# Expression Parser (Perfect as-is)
s2s/parsers/expression_parser.py → src/parsers/expression_parser.py

# Utilities
s2s/utils/file_handler.py → src/utils/file_handler.py
s2s/utils/logging_config.py → src/utils/logging_config.py

# Configuration
s2s/config/settings.py → src/config/settings.py

# Mapping YAML files
s2s/config/parameter_mappings.yml → src/mapping/mappings/mosfet_mappings.yml
s2s/config/bjt_parameter_mappings.yml → src/mapping/mappings/bjt_mappings.yml
s2s/config/diode_parameter_mappings.yml → src/mapping/mappings/diode_mappings.yml
s2s/config/capacitor_parameter_mappings.yml → src/mapping/mappings/passive_mappings.yml
```

### ⚠️ **Modify for IR Output (Add parse_to_ir Method)**

These files need the `parse_to_ir()` method added:

```python
# Current method:
def parse(self, follow_includes=False) -> List[Dict[str, Any]]:
    """Returns list of dictionaries"""
    pass

# New method to add:
def parse_to_ir(self, follow_includes=False) -> List[ModelIR]:
    """Returns list of ModelIR objects"""
    models_dict = self.parse(follow_includes)
    return [self._dict_to_ir(m) for m in models_dict]

def _dict_to_ir(self, model_dict: Dict[str, Any]) -> ModelIR:
    """Convert parsed dictionary to ModelIR"""
    return ModelIR(
        name=model_dict['name'],
        device_type=model_dict['category'],
        base_model=model_dict['type'],
        base_parameters=model_dict['parameters'],
        source_format=self.get_format_name()
    )
```

**Files to modify:**
- `s2s/parsers/base_parser.py` → `src/parsers/base_parser.py`
- `s2s/parsers/spectre_parser.py` → `src/parsers/spectre_parser.py`
- `s2s/parsers/hspice_parser.py` → `src/parsers/hspice_parser.py`
- `s2s/parsers/ngspice_parser.py` → `src/parsers/ngspice_parser.py`

### 🔄 **Refactor (Major Changes)**

These components need significant restructuring:

#### Current Translators → Split into Writers

```python
# OLD: SpectreToNgspiceTranslator (direct translation)
class SpectreToNgspiceTranslator:
    def translate_model(self, spectre_model: Dict) -> Dict:
        # Direct format-to-format logic
        pass

# NEW: NgspiceWriter (writes from IR)
class NgspiceWriter(BaseWriter):
    def write_from_ir(self, models: List[ModelIR], output: Path) -> None:
        for model in models:
            syntax = self._generate_syntax(model)
            # Write to file
```

**Refactor mapping:**
- `s2s/translators/spectre_to_ngspice_translator.py` → Extract → `src/writers/ngspice_writer.py`
- `s2s/translators/spectre_to_hspice_translator.py` → Extract → `src/writers/hspice_writer.py`
- `s2s/translators/hspice_to_spectre_translator.py` → Extract → `src/writers/spectre_writer.py`

#### Parameter Mapping Logic → Extract to Separate Module

```python
# OLD: Embedded in translators
class SpectreToNgspiceTranslator:
    def _map_parameter(self, param, value):
        if param == 'toxe':
            return ('tox', value)
        # ...

# NEW: Standalone mapper
class ParameterMapper:
    def map_parameter(self, param: str, source_format: str, target_format: str) -> str:
        mapping = self.mappings[(source_format, target_format)]
        return mapping.get(param, param)
```

**Refactor files:**
- `s2s/translators/parameter_mappings.py` → `src/mapping/parameter_mapper.py`
- Extract mapping logic from translators → `src/mapping/alias_resolver.py`

#### Validation Engine → Adapt for IR

```python
# OLD: Validates translated dictionaries
class ValidationEngine:
    def validate_translation(self, orig: Dict, trans: Dict) -> ValidationResult:
        pass

# NEW: Validates IR models
class IRValidator:
    def validate_ir(self, model: ModelIR) -> ValidationResult:
        errors = model.validate()  # Use built-in IR validation
        # Additional checks...
```

**Refactor files:**
- `s2s/translators/validation_engine.py` → `src/validation/ir_validator.py`
- `s2s/validation/enhanced_validation.py` → `src/validation/syntax_validator.py`

### ❌ **Do NOT Copy (Replace with New Implementation)**

These will be replaced entirely:

- `s2s/translators/base_translator.py` → Replace with `src/core/translation_engine.py`
- `s2s/translators/translator_factory.py` → Replace with factory pattern in core
- All specific translators → Replaced by Parser + Writer pairs

---

## Step-by-Step Migration Process

### Step 1: Set Up New Project Structure

```bash
# Create new workspace
mkdir -p spice-translator-ir
cd spice-translator-ir

# Create directory structure
mkdir -p src/{core,ir,parsers,writers,mapping,validation,utils,config}
mkdir -p tests/{test_ir,test_parsers,test_writers,test_mapping,test_validation,test_integration}
mkdir -p docs examples scripts

# Initialize git
git init
```

### Step 2: Copy Direct Files

```bash
# Copy utilities (no changes)
cp ../spice-translator/s2s/parsers/expression_parser.py src/parsers/
cp ../spice-translator/s2s/utils/file_handler.py src/utils/
cp ../spice-translator/s2s/utils/logging_config.py src/utils/
cp ../spice-translator/s2s/config/settings.py src/config/

# Copy mapping YAML files
cp ../spice-translator/s2s/config/*_mappings.yml src/mapping/mappings/
```

### Step 3: Implement Phase 1 (IR Foundation)

Follow `NEW2026_Phase1.md`:
- Create `src/ir/model_ir.py`
- Create `src/ir/ir_serializer.py`
- Create `src/parsers/base_parser.py`
- Create `src/writers/base_writer.py`
- Write tests

### Step 4: Adapt Parsers (Phase 2)

```bash
# Copy parsers
cp ../spice-translator/s2s/parsers/spectre_parser.py src/parsers/
cp ../spice-translator/s2s/parsers/hspice_parser.py src/parsers/
cp ../spice-translator/s2s/parsers/ngspice_parser.py src/parsers/
```

Then modify each to add `parse_to_ir()` method (see Phase 2 document).

### Step 5: Implement Writers (Phase 3)

Extract syntax generation from translators:
- `SpectreToNgspiceTranslator._generate_ngspice_syntax()` → `NgspiceWriter._generate_syntax()`
- Similar for HSPICE and Spectre writers

### Step 6: Extract Parameter Mapping (Phase 4)

```bash
# Copy parameter mapping base
cp ../spice-translator/s2s/translators/parameter_mappings.py src/mapping/

# Refactor into:
# - parameter_mapper.py (core mapping logic)
# - alias_resolver.py (handle parameter aliases)
# - mapping_discovery.py (self-learning system)
```

### Step 7: Adapt Validation (Phase 5)

```bash
# Copy validation components
cp ../spice-translator/s2s/validation/enhanced_validation.py src/validation/
cp ../spice-translator/s2s/translators/validation_engine.py src/validation/

# Refactor for IR:
# - ir_validator.py (validate IR structure)
# - syntax_validator.py (validate output syntax)
# - parameter_validator.py (validate ranges)
```

### Step 8: Implement CLI (Phase 6)

```bash
# Copy main CLI structure
cp ../spice-translator/s2s/main.py src/main.py

# Adapt for new engine:
# - Replace translator creation with TranslationEngine
# - Update command handlers
```

---

## File-by-File Migration Checklist

### Parsers (8 files)

- [ ] `expression_parser.py` - ✅ Copy as-is
- [ ] `base_parser.py` - ⚠️ Add `parse_to_ir()` method
- [ ] `spectre_parser.py` - ⚠️ Add `parse_to_ir()` method  
- [ ] `hspice_parser.py` - ⚠️ Add `parse_to_ir()` method
- [ ] `ngspice_parser.py` - ⚠️ Add `parse_to_ir()` method
- [ ] `generic_parser.py` - ⚠️ Optional, add if needed

### Utilities (5 files)

- [ ] `file_handler.py` - ✅ Copy as-is
- [ ] `logging_config.py` - ✅ Copy as-is
- [ ] `settings.py` - ✅ Copy as-is

### Mapping (6 files)

- [ ] `parameter_mappings.py` - 🔄 Refactor into mapper + resolver
- [ ] `mosfet_mappings.yml` - ✅ Copy as-is
- [ ] `bjt_mappings.yml` - ✅ Copy as-is
- [ ] `diode_mappings.yml` - ✅ Copy as-is
- [ ] `passive_mappings.yml` - ✅ Copy as-is

### Validation (3 files)

- [ ] `enhanced_validation.py` - 🔄 Adapt for IR
- [ ] `validation_engine.py` - 🔄 Adapt for IR

### Testing (10+ files)

- [ ] `conftest.py` - ⚠️ Adapt for new structure
- [ ] Test fixtures - ⚠️ Update import paths
- [ ] Integration tests - ⚠️ Rewrite for IR workflow

---

## Code Examples: Before → After

### Example 1: Simple Translation

**OLD (5 Translators):**
```python
from s2s.translators import create_translator

translator = create_translator('spectre', 'ngspice')
result = translator.translate_file('input.scs', 'output.lib')
```

**NEW (IR-Based):**
```python
from src.core.translation_engine import TranslationEngine

engine = TranslationEngine()
result = engine.translate(
    input_file='input.scs',
    output_file='output.lib',
    source_format='spectre',
    target_format='ngspice'
)
```

### Example 2: Parser Usage

**OLD:**
```python
from s2s.parsers import SpectreParser

parser = SpectreParser('models.scs')
models_dict = parser.parse()  # Returns List[Dict]

# models_dict = [{'name': 'nch', 'type': 'bsim4', 'parameters': {...}}]
```

**NEW:**
```python
from src.parsers.spectre_parser import SpectreParser

parser = SpectreParser(Path('models.scs'))
models_ir = parser.parse_to_ir()  # Returns List[ModelIR]

# models_ir = [ModelIR(name='nch', device_type='nmos', ...)]
```

### Example 3: Parameter Mapping

**OLD (Embedded in Translator):**
```python
class SpectreToNgspiceTranslator:
    def translate_model(self, model):
        new_params = {}
        for param, value in model['parameters'].items():
            if param == 'toxe':
                new_params['tox'] = value
            elif param == 'vth0':
                new_params['vto'] = value
            # ...
```

**NEW (Standalone Mapper):**
```python
from src.mapping.parameter_mapper import ParameterMapper

mapper = ParameterMapper()
new_params = mapper.map_parameters(
    model.base_parameters,
    source_format='spectre',
    target_format='ngspice'
)
# {'toxe': 1.5e-9} → {'tox': 1.5e-9}
```

---

## Testing After Migration

### Unit Tests
```bash
# Test IR components
pytest tests/test_ir/ -v --cov=src/ir

# Test parsers
pytest tests/test_parsers/ -v --cov=src/parsers

# Test writers
pytest tests/test_writers/ -v --cov=src/writers
```

### Integration Tests
```bash
# Test complete workflow
pytest tests/test_integration/ -v --cov=src
```

### Coverage Goals
- IR layer: >90%
- Parsers: >85%
- Writers: >85%
- Mapping: >80%
- Validation: >80%
- Overall: >80%

---

## Timeline

| Week | Phase | Focus |
|------|-------|-------|
| 1-2 | Phase 1 | IR Foundation |
| 3-4 | Phase 2 | Parsers |
| 5-6 | Phase 3 | Writers |
| 7-8 | Phase 4 | Mapping System |
| 9-10 | Phase 5 | Validation |
| 11-12 | Phase 6 | CLI & Integration |

---

## Benefits of Migration

### Before (Current Project)
- 5+ separate translator classes
- Duplicated logic across translators
- Hard to add new formats
- Parameter mapping embedded in translators
- Difficult to test individual components

### After (IR-Based)
- Single IR representation
- Shared parser/writer logic
- Easy to add formats (1 parser + 1 writer)
- Centralized parameter mapping
- Each component independently testable
- Better maintainability

---

## Success Metrics

✅ **Code Quality:**
- All files <1000 lines
- 100% type annotations
- Complete docstrings
- Zero TODO comments

✅ **Testing:**
- >80% code coverage
- All tests passing
- pytest only

✅ **Functionality:**
- All 3 formats supported (Spectre, HSPICE, ngspice)
- Parameter mapping working
- Validation pipeline functional
- CLI working

✅ **Performance:**
- <1 second per model file
- <10 seconds for batch (100 models)

---

## Questions & Troubleshooting

### Q: Can I use both old and new code during migration?
**A:** Yes! Keep the old project running while implementing the new one. Run parallel tests to ensure parity.

### Q: What if I find bugs in the old code during migration?
**A:** Fix them in the new implementation, document the fixes.

### Q: How do I handle vendor-specific parameters?
**A:** Use the parameter mapper's vendor-specific registry. Unknown parameters are passed through with warnings.

### Q: Should I migrate tests too?
**A:** Yes, but rewrite them for the new architecture. Use the old tests as reference for test cases.

---

## Contact & Support

- **Documentation:** See `docs/` folder in new project
- **Issues:** Track in project issue tracker
- **Questions:** Refer to phase documents (NEW2026_Phase1.md through Phase6.md)

---

**Document Status:** ✅ Complete  
**Last Updated:** January 4, 2026  
**Maintainer:** SPICE Translator Team
