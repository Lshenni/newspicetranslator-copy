#!/usr/bin/env python3
"""
Project Health Check
Validates project structure, dependencies, and critical functionality
"""

import sys
from pathlib import Path
from typing import List, Tuple

# Color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def check_mark(passed: bool) -> str:
    return f"{GREEN}✅{RESET}" if passed else f"{RED}❌{RESET}"

def check_python_version() -> bool:
    """Check if Python version is 3.10+"""
    version = sys.version_info
    is_valid = version.major == 3 and version.minor >= 10
    print(f"{check_mark(is_valid)} Python {version.major}.{version.minor}.{version.micro}", end="")
    if not is_valid:
        print(f" {RED}(requires 3.10+){RESET}")
    else:
        print()
    return is_valid

def check_file_exists(filepath: Path, description: str) -> bool:
    """Check if a file exists"""
    exists = filepath.exists()
    print(f"{check_mark(exists)} {description}: {filepath}")
    return exists

def check_directory_structure() -> Tuple[int, int]:
    """Check if critical directories exist"""
    critical_dirs = [
        "src/parsers",
        "src/writers",
        "src/ir",
        "src/lowering",
        "src/validation",
        "src/mapping",
        "src/s2s/translators",
        "verification",
        "simulators",
        "tests",
        "docs",
    ]
    
    passed = 0
    for dir_path in critical_dirs:
        path = Path(dir_path)
        if check_file_exists(path, f"Directory {dir_path}"):
            passed += 1
    
    return passed, len(critical_dirs)

def check_critical_files() -> Tuple[int, int]:
    """Check if critical files exist"""
    critical_files = [
        ("README.md", "Main documentation"),
        ("USAGE_GUIDE.md", "Usage guide"),
        ("VERIFICATION_FRAMEWORK.md", "Verification docs"),
        ("requirements.txt", "Dependencies"),
        ("setup.py", "Setup script"),
        ("cli.py", "CLI interface"),
        ("src/main.py", "Main translation engine"),
        ("verification/testbench_generator.py", "Testbench generator"),
        ("verification/metrics_extractor.py", "Metrics extractor"),
        ("verification/comparators.py", "Comparator"),
        ("verification/verifier.py", "Verifier"),
    ]
    
    passed = 0
    for filepath, desc in critical_files:
        if check_file_exists(Path(filepath), desc):
            passed += 1
    
    return passed, len(critical_files)

def check_imports() -> Tuple[int, int]:
    """Check if critical modules can be imported"""
    imports = [
        ("yaml", "PyYAML"),
        ("pathlib", "pathlib"),
        ("pytest", "pytest"),
    ]
    
    passed = 0
    for module, name in imports:
        try:
            __import__(module)
            print(f"{GREEN}✅{RESET} Import {name}")
            passed += 1
        except ImportError:
            print(f"{RED}❌{RESET} Import {name} {YELLOW}(run: pip install -r requirements.txt){RESET}")
    
    return passed, len(imports)

def check_project_modules() -> Tuple[int, int]:
    """Check if project modules can be imported"""
    sys.path.insert(0, str(Path.cwd()))
    
    modules = [
        "src.main",
        "src.parsers.spectre_parser",
        "src.parsers.ngspice_parser",
        "src.parsers.hspice_parser",
        "src.writers.spectre_writer",
        "src.writers.ngspice_writer",
        "src.writers.hspice_writer",
        "src.ir.model_ir",
        "verification.testbench_generator",
        "verification.metrics_extractor",
        "verification.comparators",
        "verification.verifier",
    ]
    
    passed = 0
    for module in modules:
        try:
            __import__(module)
            print(f"{GREEN}✅{RESET} Module {module}")
            passed += 1
        except Exception as e:
            print(f"{RED}❌{RESET} Module {module}: {str(e)[:50]}")
    
    return passed, len(modules)

def count_test_files() -> int:
    """Count test files"""
    test_files = list(Path('tests').rglob('test_*.py'))
    print(f"{BLUE}ℹ️{RESET}  Found {len(test_files)} test files")
    return len(test_files)

def count_source_lines() -> int:
    """Count source code lines"""
    total_lines = 0
    for pyfile in Path('src').rglob('*.py'):
        with open(pyfile) as f:
            total_lines += len(f.readlines())
    
    for pyfile in Path('verification').rglob('*.py'):
        with open(pyfile) as f:
            total_lines += len(f.readlines())
    
    for pyfile in Path('simulators').rglob('*.py'):
        with open(pyfile) as f:
            total_lines += len(f.readlines())
    
    print(f"{BLUE}ℹ️{RESET}  Total source lines: {total_lines:,}")
    return total_lines

def main():
    print(f"{BLUE}═══════════════════════════════════════{RESET}")
    print(f"{BLUE}  SPICE Translator - Health Check{RESET}")
    print(f"{BLUE}═══════════════════════════════════════{RESET}")
    print()
    
    results = {}
    
    # Check Python version
    print(f"{BLUE}[1/7] Checking Python Version{RESET}")
    results['python'] = (1 if check_python_version() else 0, 1)
    print()
    
    # Check directory structure
    print(f"{BLUE}[2/7] Checking Directory Structure{RESET}")
    results['dirs'] = check_directory_structure()
    print()
    
    # Check critical files
    print(f"{BLUE}[3/7] Checking Critical Files{RESET}")
    results['files'] = check_critical_files()
    print()
    
    # Check dependencies
    print(f"{BLUE}[4/7] Checking Dependencies{RESET}")
    results['imports'] = check_imports()
    print()
    
    # Check project modules
    print(f"{BLUE}[5/7] Checking Project Modules{RESET}")
    results['modules'] = check_project_modules()
    print()
    
    # Check tests
    print(f"{BLUE}[6/7] Checking Tests{RESET}")
    test_count = count_test_files()
    results['tests'] = (test_count, test_count)
    print()
    
    # Count source lines
    print(f"{BLUE}[7/7] Analyzing Codebase{RESET}")
    count_source_lines()
    print()
    
    # Summary
    print(f"{BLUE}═══════════════════════════════════════{RESET}")
    print(f"{BLUE}  Summary{RESET}")
    print(f"{BLUE}═══════════════════════════════════════{RESET}")
    
    total_passed = sum(r[0] for r in results.values())
    total_checks = sum(r[1] for r in results.values())
    percentage = (total_passed / total_checks * 100) if total_checks > 0 else 0
    
    for category, (passed, total) in results.items():
        status = f"{GREEN}✅{RESET}" if passed == total else f"{YELLOW}⚠️{RESET}" if passed > total * 0.7 else f"{RED}❌{RESET}"
        print(f"{status} {category.capitalize()}: {passed}/{total}")
    
    print()
    print(f"Overall Health: {total_passed}/{total_checks} ({percentage:.1f}%)")
    
    if percentage >= 90:
        print(f"{GREEN}✅ Project is healthy!{RESET}")
        return 0
    elif percentage >= 70:
        print(f"{YELLOW}⚠️  Project has minor issues{RESET}")
        return 1
    else:
        print(f"{RED}❌ Project has critical issues{RESET}")
        return 2

if __name__ == "__main__":
    sys.exit(main())
