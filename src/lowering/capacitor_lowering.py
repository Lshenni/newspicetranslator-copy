"""
Capacitor lowering pass.

Converts physical capacitor models to electrical primitives.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class LoweredCapacitor:
    """
    Lowered capacitor representation.
    
    Converts physics (area density, sidewall) to electrical (explicit C elements).
    """
    name: str
    ports: List[str]
    geometry_params: Dict[str, Any]
    area_capacitor: Optional[str] = None
    sidewall_capacitor: Optional[str] = None
    series_resistor: Optional[str] = None
    parameters: List[str] = None
    functions: List[str] = None
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = []
        if self.functions is None:
            self.functions = []


class CapacitorLowering:
    """
    Lowers physical capacitor models to ngspice primitives.
    
    Transforms:
        model capacitor cj=X cjsw=Y
    Into:
        Carea P M {X * area}
        Csw P M {Y * perim}
    """
    
    def __init__(self, backend: str = 'ngspice'):
        """Initialize lowering pass."""
        self.backend = backend
        
    def lower_capacitor(
        self,
        subckt_name: str,
        ports: List[str],
        parameters: Dict[str, Any],
        elements: List[str],
        statistical: Optional[Any] = None
    ) -> LoweredCapacitor:
        """
        Lower a physical capacitor model to electrical primitives.
        
        Args:
            subckt_name: Subcircuit name
            ports: Port names
            parameters: Geometry and electrical parameters
            elements: Original element lines
            statistical: Statistical block
            
        Returns:
            LoweredCapacitor with proper ngspice syntax
        """
        logger.info(f"Lowering capacitor: {subckt_name}")
        
        lowered = LoweredCapacitor(
            name=subckt_name,
            ports=ports,
            geometry_params={}
        )
        
        # Extract geometry parameters
        geometry_params = {}
        for param in ['area', 'perim', 'geo_fac']:
            if param in parameters:
                geometry_params[param] = parameters[param]
        
        lowered.geometry_params = geometry_params
        
        # Parse model parameters from elements
        model_params = self._extract_model_parameters(elements)
        
        # Extract capacitance densities
        cj = model_params.get('cj', '1e-3')
        cjsw = model_params.get('cjsw', '1e-10')
        tc1 = model_params.get('tc1')
        tc2 = model_params.get('tc2')
        
        # Build mismatch expression if statistical
        mismatch_expr = self._build_mismatch_expression(
            statistical, geometry_params
        )
        
        # Build lowering parameters and functions
        lowered.parameters = self._build_parameters(
            geometry_params, statistical, mismatch_expr
        )
        lowered.functions = self._build_functions(statistical)
        
        # Build area capacitor
        area_expr = self._build_area_capacitor_expr(
            cj, mismatch_expr, 'area'
        )
        lowered.area_capacitor = f"Carea {ports[0]} M2 {area_expr}"
        
        # Build sidewall capacitor
        sw_expr = self._build_sidewall_capacitor_expr(
            cjsw, mismatch_expr, 'perim'
        )
        lowered.sidewall_capacitor = f"Csw {ports[0]} M2 {sw_expr}"
        
        # Build series resistor
        lowered.series_resistor = f"Rs M2 {ports[1]} 1"
        
        logger.info(
            f"Lowered {subckt_name}: area_cap, sw_cap, series_r, "
            f"{len(lowered.parameters)} params"
        )
        
        return lowered
    
    def _extract_model_parameters(self, elements: List[str]) -> Dict[str, str]:
        """Extract parameters from model line in elements."""
        import re
        
        params = {}
        for elem in elements:
            if 'model' in elem and 'capacitor' in elem:
                # Extract param=value pairs
                for match in re.finditer(r'(\w+)=([\S]+)', elem):
                    params[match.group(1)] = match.group(2)
        
        return params
    
    def _build_mismatch_expression(
        self,
        statistical: Optional[Any],
        geometry_params: Dict[str, Any]
    ) -> str:
        """Build mismatch expression for Monte Carlo."""
        if not statistical or not hasattr(statistical, 'variables'):
            return "1"
        
        # Extract statistical variable (e.g., pc_mc)
        var_name = None
        sigma = "0.002"  # Default 0.2%
        
        for var, info in statistical.variables.items():
            var_name = var
            std_str = info.get('std', '1/1')
            # Parse std (could be "1/1" or "0.002")
            if '/' in std_str:
                parts = std_str.split('/')
                if len(parts) == 2 and parts[0] == parts[1]:
                    sigma = "0.002"  # 1/1 → 0.2% mismatch
            break
        
        if not var_name:
            return "1"
        
        # Build geometry-scaled mismatch
        geo_fac = geometry_params.get('geo_fac', '1')
        
        # Expression: (1 - 2m * pc_mc * geo_fac)
        # Convert to: (1 + mc_en * mc_gauss() * sigma * geo_fac)
        return f"(1 + mc_en*mc_gauss()*{sigma}*geo_fac)"
    
    def _build_parameters(
        self,
        geometry_params: Dict[str, Any],
        statistical: Optional[Any],
        mismatch_expr: str
    ) -> List[str]:
        """Build .param declarations."""
        params = []
        
        # Geometry scaling
        geo_fac = geometry_params.get('geo_fac', '1')
        if geo_fac != '1':
            # Normalize expression
            geo_fac_clean = geo_fac.replace('5u', '5e-6')
            params.append(f".param geo_fac={geo_fac_clean}")
        
        # Monte Carlo control
        if statistical:
            params.append(".param mc_en=0")
            params.append(".param cap_var=1")  # Corner variation
        
        # Mismatch expression
        if mismatch_expr != "1":
            params.append(f".param mismatch={mismatch_expr}")
        
        return params
    
    def _build_functions(self, statistical: Optional[Any]) -> List[str]:
        """Build .func declarations."""
        funcs = []
        
        if statistical and hasattr(statistical, 'variables'):
            # Use gauss() not agauss() for ngspice compatibility
            funcs.append(".func mc_gauss() {gauss(0,1)}")
        
        return funcs
    
    def _build_area_capacitor_expr(
        self,
        cj: str,
        mismatch_expr: str,
        area_param: str
    ) -> str:
        """Build area capacitor expression."""
        # cj * area * mismatch * cap_var
        
        # Parse cj to extract base value
        import re
        cj_clean = cj
        
        # If cj contains expression like (1-2m*pc_mc*geo_fac)*cap_var*1e-3
        # Extract just the density: 1e-3
        match = re.search(r'(\d+\.?\d*e-\d+)', cj)
        if match:
            density = match.group(1)
        else:
            density = "1e-3"
        
        if mismatch_expr != "1":
            return f"{{cap_var*{density}*{area_param}*mismatch}}"
        else:
            return f"{{cap_var*{density}*{area_param}}}"
    
    def _build_sidewall_capacitor_expr(
        self,
        cjsw: str,
        mismatch_expr: str,
        perim_param: str
    ) -> str:
        """Build sidewall capacitor expression."""
        import re
        
        # Extract density from cjsw expression
        match = re.search(r'(\d+\.?\d*e-\d+)', cjsw)
        if match:
            density = match.group(1)
        else:
            density = "1e-10"
        
        if mismatch_expr != "1":
            return f"{{cap_var*{density}*{perim_param}*mismatch}}"
        else:
            return f"{{cap_var*{density}*{perim_param}}}"
