"""
Backend capability matrix.

Defines what each simulator backend supports.
"""

from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class Capabilities:
    """Simulator capabilities."""
    
    # Capacitor support
    capacitor_density_model: bool = False  # Supports cj/cjsw in .model
    expression_based_capacitor: bool = True  # Supports C{expr}
    
    # Statistical support
    statistics_block: bool = False  # Native statistics
    monte_carlo_functions: bool = True  # gauss(), agauss()
    agauss_function: bool = False  # Specifically agauss()
    
    # Subcircuit support
    inline_model_instantiation: bool = False  # Can instantiate models in subckt
    
    # Temperature support
    temperature_coefficients: bool = True  # tc1, tc2
    
    # Expression support
    braced_expressions: bool = True  # { expr }
    
    def supports(self, feature: str) -> bool:
        """Check if feature is supported."""
        return getattr(self, feature, False)


class BackendCapabilities:
    """Backend capability definitions."""
    
    CAPABILITIES: Dict[str, Capabilities] = {
        'ngspice': Capabilities(
            capacitor_density_model=False,  # ❌ No cj/cjsw in .model
            expression_based_capacitor=True,  # ✅ C { expr }
            statistics_block=False,  # ❌ No statistics
            monte_carlo_functions=True,  # ✅ gauss()
            agauss_function=False,  # ❌ Use gauss() instead
            inline_model_instantiation=False,  # ❌ No model wrapping
            temperature_coefficients=False,  # ⚠️ Limited TC support
            braced_expressions=True,  # ✅ { expr }
        ),
        
        'hspice': Capabilities(
            capacitor_density_model=False,  # ❌ No cj/cjsw in .model
            expression_based_capacitor=True,  # ✅ C='expr'
            statistics_block=False,  # ❌ Different MC syntax (.ALTER)
            monte_carlo_functions=True,  # ✅ gauss(), agauss()
            agauss_function=True,  # ✅ agauss() supported
            inline_model_instantiation=False,  # ❌ Need primitives
            temperature_coefficients=True,  # ✅ Full TC support
            braced_expressions=False,  # ❌ Use = instead of {}
        ),
        
        'spectre': Capabilities(
            capacitor_density_model=True,  # ✅ Native cj/cjsw support
            expression_based_capacitor=True,  # ✅ Full expression support
            statistics_block=True,  # ✅ Full statistics { } blocks
            monte_carlo_functions=True,  # ✅ gauss(), agauss()
            agauss_function=True,  # ✅ agauss() native
            inline_model_instantiation=True,  # ✅ Model-backed devices
            temperature_coefficients=True,  # ✅ Full TC support
            braced_expressions=True,  # ✅ { expr } syntax
        ),
    }
    
    @classmethod
    def get(cls, backend: str) -> Capabilities:
        """Get capabilities for backend."""
        return cls.CAPABILITIES.get(backend.lower(), Capabilities())
    
    @classmethod
    def supports(cls, backend: str, feature: str) -> bool:
        """Check if backend supports feature."""
        caps = cls.get(backend)
        return caps.supports(feature)
    
    @classmethod
    def requires_lowering(cls, backend: str, feature: str) -> bool:
        """Check if feature requires lowering for this backend."""
        return not cls.supports(backend, feature)
