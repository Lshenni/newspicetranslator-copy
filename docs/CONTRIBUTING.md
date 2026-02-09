# Contributing to SPICE Translator

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

---

## 🔧 Development Setup

### Prerequisites
- Python 3.10 or higher
- Git
- (Optional) ngspice, HSPICE, or Spectre for verification

### Initial Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/spice-translator.git
cd spice-translator

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"

# Run tests to verify setup
pytest tests/
```

---

## 📝 Code Style

We use:
- **Ruff** for linting and formatting
- **MyPy** for type checking
- **Pytest** for testing

### Before Committing

```bash
# Format code
ruff format .

# Check for lint errors
ruff check .

# Run type checker
mypy src/

# Run full test suite
pytest tests/ --cov=src --cov-report=html
```

---

## 🧪 Testing Guidelines

### Test Structure
```
tests/
├── test_parsers/        # Parser unit tests
├── test_writers/        # Writer unit tests
├── test_mapping/        # Parameter mapping tests
├── test_validation/     # Validator tests
├── integration/         # End-to-end tests
└── regression/          # Regression test suite
```

### Writing Tests

1. **Unit tests**: Test individual functions/classes
2. **Integration tests**: Test complete translation workflows
3. **Regression tests**: Add tests for bug fixes

Example:
```python
def test_capacitor_translation():
    """Test capacitor model translation from Spectre to ngspice"""
    input_model = """
    model capacitor capacitor cj=1e-3 cjsw=1e-10
    """
    expected_output = """
    .model capacitor c ...
    """
    # Test implementation
```

### Coverage Requirements
- Maintain >80% code coverage
- All new features must include tests
- Bug fixes must include regression tests

---

## 🌟 Adding New Features

### 1. Device Type Support

To add a new device type (e.g., inductor):

1. Update `src/ir/model_ir.py`:
   ```python
   class InductorModel(ModelIR):
       device_type = "inductor"
       # Define parameters
   ```

2. Add parser support in `src/parsers/`:
   - Update `spectre_parser.py`, `hspice_parser.py`, `ngspice_parser.py`

3. Add writer support in `src/writers/`:
   - Implement device-specific formatting

4. Add lowering logic in `src/lowering/`:
   ```python
   # inductor_lowering.py
   class InductorLowering:
       def lower(self, model, target):
           # Lowering logic
   ```

5. Add verification support:
   - Update `verification/testbench_generator.py`
   - Update `verification/metrics_extractor.py`
   - Add tolerance configuration in `verification/comparators.py`

6. Add tests:
   ```python
   # tests/test_lowering/test_inductor_lowering.py
   def test_inductor_spectre_to_ngspice():
       # Test implementation
   ```

### 2. Backend Support

To add a new SPICE simulator (e.g., LTspice):

1. Create parser: `src/parsers/ltspice_parser.py`
2. Create writer: `src/writers/ltspice_writer.py`
3. Update translators: `src/s2s/translators/`
4. Add simulator wrapper: `simulators/run_simulator.py`
5. Update CLI: `cli.py`

---

## 📚 Documentation

### Docstring Format
Use Google-style docstrings:

```python
def translate_model(input_file: Path, target: str) -> ModelIR:
    """Translate SPICE model from one format to another.
    
    Args:
        input_file: Path to input SPICE file
        target: Target simulator format ('ngspice', 'hspice', 'spectre')
    
    Returns:
        Translated model in IR format
        
    Raises:
        ParseError: If input file cannot be parsed
        TranslationError: If translation fails
        
    Example:
        >>> model = translate_model(Path('input.scs'), 'ngspice')
        >>> print(model.device_type)
        'capacitor'
    """
```

### Documentation Updates
When adding features, update:
- `README.md` - Quick start guide
- `VERIFICATION_FRAMEWORK.md` - Verification details
- `docs/` - Technical documentation
- `PROJECT_STATUS.md` - Project status

---

## 🔀 Git Workflow

### Branch Naming
- `feature/device-inductor` - New features
- `fix/capacitor-lowering-bug` - Bug fixes
- `docs/update-readme` - Documentation
- `refactor/parser-cleanup` - Refactoring

### Commit Messages
Follow conventional commits:
```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `ci`

Examples:
```
feat(lowering): Add inductor lowering support

- Implement InductorLowering class
- Add L/Q parameter extraction
- Update backend capabilities

Closes #42
```

### Pull Request Process

1. Create feature branch from `develop`
2. Make changes and commit
3. Run full test suite
4. Push and create PR to `develop`
5. Address review comments
6. Merge after approval

---

## 🐛 Reporting Bugs

### Bug Report Template
```markdown
**Description**
Clear description of the bug

**To Reproduce**
1. Input file: (attach or paste)
2. Command: `python src/main.py ...`
3. Expected behavior
4. Actual behavior

**Environment**
- OS: [e.g., Ubuntu 22.04]
- Python version: [e.g., 3.12.3]
- Simulator: [e.g., ngspice 42]

**Additional Context**
Error messages, logs, etc.
```

---

## 💡 Feature Requests

Use GitHub Issues with:
- Clear use case description
- Example input/output
- Why existing features don't solve it
- Proposed implementation (optional)

---

## 📊 Verification Framework Contributions

When modifying verification framework:

1. **Testbench generation**: Update `verification/testbench_generator.py`
2. **Metrics extraction**: Update `verification/metrics_extractor.py`
3. **Tolerances**: Update `verification/comparators.py` (document why)
4. **Regression tests**: Add to `tests/regression/test_suite.py`
5. **CI**: Update `.github/workflows/verification.yml` if needed

---

## 📞 Questions?

- Open a GitHub Discussion
- Check existing Issues
- Read `VERIFICATION_FRAMEWORK.md` for verification details
- Read `docs/` for technical documentation

---

## 🏆 Recognition

Contributors will be:
- Listed in `README.md`
- Acknowledged in release notes
- Credited in academic publications (if applicable)

Thank you for contributing to SPICE Translator! 🚀
