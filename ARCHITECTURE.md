# SPICE Translator Architecture

**Version:** 3.0  
**Date:** February 1, 2026

---

## Overview

The SPICE Translator uses an **Intermediate Representation (IR)** architecture that enables format-agnostic translation between Spectre, HSPICE, and ngspice simulators.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        TRANSLATION PIPELINE                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   ┌──────────┐     ┌─────────┐     ┌──────────┐     ┌──────────┐   │
│   │  Input   │────▶│ Parser  │────▶│    IR    │────▶│  Writer  │   │
│   │  File    │     │         │     │ (ModelIR)│     │          │   │
│   └──────────┘     └─────────┘     └──────────┘     └──────────┘   │
│        │               │                │                │          │
│        ▼               ▼                ▼                ▼          │
│   .scs/.sp/.lib   SpectreParser    Validation      NgspiceWriter   │
│                   HSPICEParser     IR Validator    HSPICEWriter    │
│                   NgspiceParser                    SpectreWriter   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Parsers (`src/parsers/`)

Convert format-specific syntax to universal IR.

| Parser | Format | Extensions |
|--------|--------|------------|
| `SpectreParser` | Cadence Spectre | `.scs` |
| `HSPICEParser` | Synopsys HSPICE | `.sp`, `.lib`, `.mdl` |
| `NgspiceParser` | ngspice | `.lib`, `.cir` |
| `ExpressionParser` | Math expressions | All formats |

**Key Features:**
- Section/corner handling (`section tt`, `.lib tt`)
- Subcircuit extraction
- Include file following
- Parameter expression parsing

### 2. Intermediate Representation (`src/ir/`)

Format-agnostic model representation.

```python
@dataclass
class ModelIR:
    name: str                           # Model name
    device_type: DeviceType             # NMOS, PNP, DIODE, etc.
    base_model: str                     # bsim4, level=54, etc.
    base_parameters: Dict[str, Any]     # Parameter values
    variations: List[ModelVariation]    # Corner variations
    source_format: str                  # Origin format
```

**Device Types:**
- `NMOS`, `PMOS` - MOSFETs
- `NPN`, `PNP` - BJTs
- `DIODE` - Diodes
- `RESISTOR`, `CAPACITOR`, `INDUCTOR` - Passives
- `SUBCIRCUIT` - Subcircuits

### 3. Writers (`src/writers/`)

Convert IR to target format syntax.

| Writer | Target | Key Features |
|--------|--------|--------------|
| `NgspiceWriter` | ngspice | `{expr}` wrapping, `.param` defaults |
| `HSPICEWriter` | HSPICE | `'expr'` syntax, `.lib/.endl` blocks |
| `SpectreWriter` | Spectre | Native Spectre sections |

**ngspice Writer Capabilities:**
- Expression brace wrapping `{...}`
- Boolean normalization (`yes`→`1`, `no`→`0`)
- Auto `.param` for referenced symbols
- Inline subcircuit model conversion
- Primitive instance conversion (`resistor r=...` → `R...`)

### 4. Validation (`src/validation/`)

Multi-stage validation pipeline.

| Validator | Purpose |
|-----------|---------|
| `IRValidator` | Check IR structure completeness |
| `SyntaxValidator` | Verify output syntax correctness |
| `ParameterValidator` | Validate parameter ranges |
| `TranslationValidator` | Compare source vs. target |

### 5. Verification (`verification/`)

End-to-end simulation-based verification.

```
┌──────────┐    ┌───────────┐    ┌───────────┐    ┌────────────┐
│ Translate│───▶│ Generate  │───▶│ Simulate  │───▶│  Compare   │
│          │    │ Testbench │    │ (ngspice) │    │  Metrics   │
└──────────┘    └───────────┘    └───────────┘    └────────────┘
```

**Components:**
- `TestbenchGenerator` - Device-specific testbenches
- `MetricsExtractor` - Scalar FOM extraction
- `Comparator` - Tolerance-based pass/fail
- `Verifier` - Orchestration layer

### 6. Simulators (`simulators/`)

Unified simulation interface.

```python
from simulators import run_simulation, SimulationResult

result: SimulationResult = run_simulation(
    netlist=netlist_content,
    simulator='ngspice',
    output_dir=Path('sim_output/')
)

# Result includes:
# - success: bool
# - status: 'passed' | 'failed' | 'skipped'
# - skip_reason: 'unsupported_mos_level' | None
# - stdout, stderr, output_file
```

---

## Directory Structure

```
new-spice-translator/
├── src/
│   ├── ir/                         # Intermediate Representation
│   │   ├── model_ir.py             # ModelIR, DeviceType, Condition
│   │   └── ir_serializer.py        # JSON/YAML serialization
│   │
│   ├── parsers/                    # Format Parsers
│   │   ├── base_parser.py          # Abstract parser
│   │   ├── spectre_parser.py       # Spectre → IR
│   │   ├── hspice_parser.py        # HSPICE → IR
│   │   ├── ngspice_parser.py       # ngspice → IR
│   │   └── expression_parser.py    # Math expression AST
│   │
│   ├── writers/                    # Format Writers
│   │   ├── base_writer.py          # Abstract writer
│   │   ├── ngspice_writer.py       # IR → ngspice
│   │   ├── hspice_writer.py        # IR → HSPICE
│   │   └── spectre_writer.py       # IR → Spectre
│   │
│   ├── validation/                 # Validation Pipeline
│   │   ├── ir_validator.py
│   │   ├── syntax_validator.py
│   │   └── parameter_validator.py
│   │
│   ├── lowering/                   # Semantic Lowering
│   │   └── capacitor_lowering.py   # Density → primitives
│   │
│   └── main.py                     # TranslationEngine
│
├── verification/                   # Verification Framework
│   ├── testbench_generator.py
│   ├── metrics_extractor.py
│   ├── comparators.py
│   └── verifier.py
│
├── simulators/                     # Simulator Wrappers
│   └── run_simulator.py            # ngspice/HSPICE/Spectre
│
├── tools/                          # Utilities
│   ├── rerun_private_models.py     # Corpus validation
│   └── spice-libraries/            # Test PDKs
│
├── tests/                          # pytest Suite
│   ├── test_parsers/
│   ├── test_writers/
│   └── test_validation/
│
├── cli.py                          # Command-line Interface
└── output/                         # Generated Files
```

---

## Translation Flow

### Step 1: Parse Source
```python
from src.parsers import SpectreParser

parser = SpectreParser(Path('input.scs'))
models: List[ModelIR] = parser.parse_to_ir()
```

### Step 2: Validate IR
```python
from src.validation import IRValidator

validator = IRValidator()
result = validator.validate(models)
```

### Step 3: Write Target
```python
from src.writers import NgspiceWriter

writer = NgspiceWriter(Path('output.lib'))
writer.write_from_ir(models)
```

### Full Pipeline (via TranslationEngine)
```python
from src.main import TranslationEngine

engine = TranslationEngine()
result = engine.translate(
    input_file=Path('input.scs'),
    output_file=Path('output.lib'),
    source_format='spectre',
    target_format='ngspice',
    validate=True
)
```

---

## Key Design Decisions

### 1. IR-Based Architecture
- **Why:** Eliminates N×(N-1) translator combinations
- **Benefit:** Add new format with 1 parser + 1 writer

### 2. Expression Brace Wrapping
- **Why:** ngspice requires `{...}` for parameter expressions
- **Implementation:** `NgspiceWriter._format_value()` wraps all expressions

### 3. Auto Parameter Defaults
- **Why:** ngspice fails on undefined parameters in expressions
- **Implementation:** Scan expressions, emit `.param sym=0` for undefined

### 4. Skip Classification
- **Why:** Distinguish simulator limits from translator bugs
- **Implementation:** `SimulationResult.status='skipped'` + `skip_reason`

### 5. Inline Subcircuit Handling
- **Why:** Spectre allows model cards inside subcircuits
- **Implementation:** Join continuation lines, convert primitives

---

## Backend Capability Matrix

| Feature | ngspice | HSPICE | Spectre |
|---------|---------|--------|---------|
| MOS Levels | 1-6,8-10,14,49,54-58,60,68,73 | All | All |
| BSIM-CMG (72) | ❌ (build-dependent) | ✅ | ✅ |
| Expression syntax | `{expr}` | `'expr'` | Native |
| Density capacitors | ❌ (lowered to C) | ❌ | ✅ |
| Statistics | ❌ (flattened) | Limited | ✅ |

---

## Extension Points

### Adding a New Parser
1. Create `src/parsers/new_parser.py`
2. Inherit from `BaseParser`
3. Implement `parse_to_ir()` → `List[ModelIR]`

### Adding a New Writer
1. Create `src/writers/new_writer.py`
2. Inherit from `BaseWriter`
3. Implement `write_from_ir(models: List[ModelIR])`

### Adding Device Type Support
1. Add to `DeviceType` enum in `src/ir/model_ir.py`
2. Update parser device classification
3. Update writer syntax generation

---

## Performance Characteristics

| Operation | Typical Time |
|-----------|--------------|
| Parse (per file) | 10-50 ms |
| Write (per file) | 10-30 ms |
| Full translation | 50-200 ms |
| ngspice smoke sim | 200-500 ms |
| Corpus (113 files) | ~45 seconds |

---

## Testing

```bash
# Unit tests
pytest tests/ -v

# Coverage report
pytest tests/ --cov=src --cov-report=html

# Corpus validation
python tools/rerun_private_models.py --simulate-ngspice
```

**Current Test Status:**
- 569 tests passing
- 84% code coverage
- 15 tests skipped (optional features)
