"""
SPICE Translator with Verification Framework
Setup configuration for installation
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

setup(
    name="spice-translator",
    version="3.0.0",
    description="Production-grade SPICE model translator with semantic lowering and verification framework",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://github.com/yourusername/spice-translator",
    license="MIT",
    
    # Package configuration
    packages=find_packages(exclude=["tests", "tests.*", "docs", "tools"]),
    package_dir={"": "."},
    
    # Dependencies
    install_requires=[
        "pyyaml>=6.0",
        "pathlib2>=2.3.7",
        "tqdm>=4.65.0",
    ],
    
    # Development dependencies
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
            "pytest-xdist>=3.0",
            "ruff>=0.1.0",
            "mypy>=1.0",
        ],
        "verification": [
            # Add simulator-specific dependencies if needed
        ],
    },
    
    # Python version requirement
    python_requires=">=3.10",
    
    # Entry points for CLI
    entry_points={
        "console_scripts": [
            "spice-translator=cli:main",
        ],
    },
    
    # Classifiers for PyPI
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering :: Electronic Design Automation (EDA)",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    
    # Include additional files
    include_package_data=True,
    zip_safe=False,
    
    # Keywords for discoverability
    keywords="spice eda semiconductor translator ngspice hspice spectre verification",
)
