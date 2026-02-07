"""
Automatic Testbench Generator

Generates device-class-specific simulation testbenches for verification.
Testbenches are semantically identical across simulators, with only syntax differences.

Key Principle: Testbenches must produce comparable scalar metrics, not waveforms.
"""

from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Union
from dataclasses import dataclass


class DeviceClass(Enum):
    """Supported device classes for testbench generation"""
    CAPACITOR = "capacitor"
    RESISTOR = "resistor"
    MOS = "mos"
    BJT = "bjt"
    DIODE = "diode"


@dataclass
class TestbenchConfig:
    """Configuration for testbench generation"""
    device_name: str
    device_class: DeviceClass
    format: str  # 'ngspice', 'hspice', 'spectre'
    monte_carlo_runs: int = 0
    temp_sweep: Optional[List[float]] = None
    corner: Optional[str] = None
    area: Optional[float] = None
    perim: Optional[float] = None
    width: Optional[float] = None
    length: Optional[float] = None


class TestbenchGenerator:
    """
    Generates device-specific testbenches for verification
    
    Usage:
        gen = TestbenchGenerator()
        netlist = gen.generate_cap_ac_test("mimcap", format='ngspice')
    """
    
    def __init__(self):
        self.generators = {
            DeviceClass.CAPACITOR: self._generate_capacitor_test,
            DeviceClass.RESISTOR: self._generate_resistor_test,
            DeviceClass.MOS: self._generate_mos_test,
            DeviceClass.BJT: self._generate_bjt_test,
            DeviceClass.DIODE: self._generate_diode_test
        }
    
    def generate(self, config: TestbenchConfig) -> str:
        """Generate testbench based on configuration"""
        generator = self.generators.get(config.device_class)
        if not generator:
            raise ValueError(f"Unsupported device class: {config.device_class}")

        # Ensure defaults are available for placeholder substitution.
        # Generators use defaults internally, but templates still contain placeholders.
        if config.device_class == DeviceClass.CAPACITOR:
            if config.area is None:
                config.area = 10e-6
            if config.perim is None:
                config.perim = 20e-6
        elif config.device_class == DeviceClass.MOS:
            if config.width is None:
                config.width = 1e-6
            if config.length is None:
                config.length = 90e-9
        
        # Generate template and substitute placeholders
        template = generator(config)
        
        # Substitute config values - handle {{placeholder}} and {config.attr} patterns
        result = template.replace('{{lib_file}}', '{lib_file}')  # Keep for later replacement
        result = result.replace('{config.device_name}', config.device_name)
        result = result.replace('{device_name}', config.device_name)
        result = result.replace('{model_name}', config.device_name)
        
        # Substitute area/perim/width/length if present
        if config.area is not None:
            result = result.replace('{area}', str(config.area))
        if config.perim is not None:
            result = result.replace('{perim}', str(config.perim))
        if config.width is not None:
            result = result.replace('{W}', str(config.width))
            result = result.replace('{width}', str(config.width))
        if config.length is not None:
            result = result.replace('{L}', str(config.length))
            result = result.replace('{length}', str(config.length))
        if config.monte_carlo_runs:
            result = result.replace('{mc_runs}', str(config.monte_carlo_runs))
        
        return result
    
    # ============================================================================
    # CAPACITOR TESTBENCHES
    # ============================================================================
    
    def _generate_capacitor_test(self, config: TestbenchConfig) -> str:
        """Generate AC impedance test for capacitor"""
        area = config.area or 10e-6  # 10um^2
        perim = config.perim or 20e-6  # 20um
        
        if config.format == 'ngspice':
            tb = self._cap_ac_ngspice(config.device_name, area, perim, config.monte_carlo_runs)
        elif config.format == 'hspice':
            tb = self._cap_ac_hspice(config.device_name, area, perim, config.monte_carlo_runs)
        elif config.format == 'spectre':
            tb = self._cap_ac_spectre(config.device_name, area, perim, config.monte_carlo_runs)
        else:
            raise ValueError(f"Unsupported format: {config.format}")
        
        return tb
    
    def _cap_ac_ngspice(self, device_name: str, area: float, perim: float, mc_runs: int = 0) -> str:
        """Capacitor AC test for ngspice"""
        if mc_runs > 0:
            # Monte Carlo AC test
            return """* Capacitor AC Verification Test (Monte Carlo)
.include {{lib_file}}

* AC voltage source
Vac P 0 AC 1

* Device under test
XU1 P 0 {device_name} area={area} perim={perim}

* Monte Carlo loop
.param mc_run = 0
.step param mc_run 1 {mc_runs} 1

.control
set wr_singlescale
set wr_vecnames
option numdgt=7

ac dec 100 1 1G

* Extract impedance at 1MHz
let freq_target = 1e6
let idx = floor(length(frequency)/2)
let Z = abs(v(P)/i(Vac))
let C_eff = 1/(2*pi*frequency[idx]*Z[idx])

print C_eff > cap_metrics_{{mc_run}}.txt
quit
.endc
.end
"""
        else:
            # Single run AC test
            return """* Capacitor AC Verification Test
.include {{lib_file}}

* AC voltage source
Vac P 0 AC 1

* Device under test
XU1 P 0 {device_name} area={area} perim={perim}

.control
set wr_singlescale
set wr_vecnames
option numdgt=7

ac dec 100 1 1G

* Extract impedance at 1MHz
let freq_target = 1e6
let idx = floor(length(frequency)/2)
let Z = abs(v(P)/i(Vac))
let C_eff = 1/(2*pi*frequency[idx]*Z[idx])

print C_eff > cap_metrics.txt
quit
.endc
.end
"""
    
    def _cap_ac_hspice(self, device_name: str, area: float, perim: float, mc_runs: int = 0) -> str:
        """Capacitor AC test for HSPICE"""
        if mc_runs > 0:
            return """* Capacitor AC Verification Test (Monte Carlo)
.include {{lib_file}}

Vac P 0 AC 1
XU1 P 0 {device_name} area={area} perim={perim}

.param mc_en=1
.ac dec 100 1 1G
.mont {mc_runs}
.measure ac C_eff param='1/(2*pi*1e6*abs(v(P)/i(Vac)))'
.print ac C_eff
.end
"""
        else:
            return """* Capacitor AC Verification Test
.include {{lib_file}}

Vac P 0 AC 1
XU1 P 0 {device_name} area={area} perim={perim}

.ac dec 100 1 1G
.measure ac C_eff param='1/(2*pi*1e6*abs(v(P)/i(Vac)))'
.print ac C_eff
.end
"""
    
    def _cap_ac_spectre(self, device_name: str, area: float, perim: float, mc_runs: int = 0) -> str:
        """Capacitor AC test for Spectre"""
        if mc_runs > 0:
            return """// Capacitor AC Verification Test (Monte Carlo)
include "{{lib_file}}"

Vac (P 0) vsource type=sine ampl=1
XU1 (P 0) {device_name} area={area} perim={perim}

mc montecarlo variations={{mismatch process} runs={mc_runs} {{
    ac ac freq=1M
    save XU1:*
}}
"""
        else:
            return """// Capacitor AC Verification Test
include "{{lib_file}}"

Vac (P 0) vsource type=sine ampl=1
XU1 (P 0) {device_name} area={area} perim={perim}

ac ac freq=1M
save XU1:*
"""
    
    # ============================================================================
    # MOS TESTBENCHES
    # ============================================================================
    
    def _generate_mos_test(self, config: TestbenchConfig) -> str:
        """Generate DC Vgs sweep for MOS"""
        W = config.width or 1e-6
        L = config.length or 90e-9
        
        if config.format == 'ngspice':
            return self._mos_dc_ngspice(config.device_name, W, L, config.monte_carlo_runs)
        elif config.format == 'hspice':
            return self._mos_dc_hspice(config.device_name, W, L, config.monte_carlo_runs)
        elif config.format == 'spectre':
            return self._mos_dc_spectre(config.device_name, W, L, config.monte_carlo_runs)
        else:
            raise ValueError(f"Unsupported format: {config.format}")
    
    def _mos_dc_ngspice(self, model_name: str, W: float, L: float, mc_runs: int = 0) -> str:
        """MOS DC sweep for ngspice"""
        if mc_runs > 0:
            return """* MOS DC Verification Test (Monte Carlo)
.include {{lib_file}}

Vgs g 0 DC 0.6
Vds d 0 DC 1.2
M1 d g 0 0 {model_name} W={W} L={L}

.param mc_run = 0
.step param mc_run 1 {mc_runs} 1

.control
dc Vgs 0 1.2 0.05
let Id = -i(Vds)
let gm = deriv(Id)
let Vth_est = Vgs[vecmin(abs(Id-1e-7))]

print Vth_est gm[20] > mos_metrics_{{mc_run}}.txt
quit
.endc
.end
"""
        else:
            return """* MOS DC Verification Test
.include {{lib_file}}

Vgs g 0 DC 0.6
Vds d 0 DC 1.2
M1 d g 0 0 {model_name} W={W} L={L}

.control
dc Vgs 0 1.2 0.05
let Id = -i(Vds)
let gm = deriv(Id)

print Id gm > mos_metrics.txt
quit
.endc
.end
"""
    
    def _mos_dc_hspice(self, model_name: str, W: float, L: float, mc_runs: int = 0) -> str:
        """MOS DC sweep for HSPICE"""
        if mc_runs > 0:
            return """* MOS DC Verification Test (Monte Carlo)
.include {{lib_file}}

Vgs g 0 DC 0.6
Vds d 0 DC 1.2
M1 d g 0 0 {model_name} W={W} L={L}

.param mc_en=1
.dc Vgs 0 1.2 0.05
.mont {mc_runs}
.measure dc Id_sat find i(Vds) at=0.6
.measure dc gm_max max deriv(i(Vds))
.print dc i(Vds)
.end
"""
        else:
            return """* MOS DC Verification Test
.include {{lib_file}}

Vgs g 0 DC 0.6
Vds d 0 DC 1.2
M1 d g 0 0 {model_name} W={W} L={L}

.dc Vgs 0 1.2 0.05
.measure dc Id_sat find i(Vds) at=0.6
.measure dc gm_max max deriv(i(Vds))
.print dc i(Vds)
.end
"""
    
    def _mos_dc_spectre(self, model_name: str, W: float, L: float, mc_runs: int = 0) -> str:
        """MOS DC sweep for Spectre"""
        if mc_runs > 0:
            return """// MOS DC Verification Test (Monte Carlo)
include "{{lib_file}}"

Vgs (g 0) vsource dc=0.6
Vds (d 0) vsource dc=1.2
M1 (d g 0 0) {model_name} w={W} l={L}

mc montecarlo variations={{mismatch process}} runs={mc_runs} {{
    dc dc dev=Vgs start=0 stop=1.2 step=0.05
    save M1:id M1:gm
}}
"""
        else:
            return """// MOS DC Verification Test
include "{{lib_file}}"

Vgs (g 0) vsource dc=0.6
Vds (d 0) vsource dc=1.2
M1 (d g 0 0) {model_name} w={W} l={L}

dc dc dev=Vgs start=0 stop=1.2 step=0.05
save M1:id M1:gm
"""
    
    # ============================================================================
    # BJT TESTBENCHES
    # ============================================================================
    
    def _generate_bjt_test(self, config: TestbenchConfig) -> str:
        """Generate Vbe sweep for BJT"""
        if config.format == 'ngspice':
            return """* BJT DC Verification Test
.include {{lib_file}}

Vbe b 0 DC 0.7
Vce c 0 DC 2.0
Q1 c b 0 {config.device_name}

.control
dc Vbe 0.4 0.9 0.02
let Ic = i(Vce)
let beta = Ic/ib(Q1)

print Ic beta > bjt_metrics.txt
quit
.endc
.end
"""
        elif config.format == 'hspice':
            return """* BJT DC Verification Test
.include {{lib_file}}

Vbe b 0 DC 0.7
Vce c 0 DC 2.0
Q1 c b 0 {config.device_name}

.dc Vbe 0.4 0.9 0.02
.measure dc Ic_07 find i(Vce) at=0.7
.measure dc beta_max max '(-i(Vce)/ib(Q1))'
.print dc i(Vce) ib(Q1)
.end
"""
        else:  # spectre
            return """// BJT DC Verification Test
include "{{lib_file}}"

Vbe (b 0) vsource dc=0.7
Vce (c 0) vsource dc=2.0
Q1 (c b 0) {config.device_name}

dc dc dev=Vbe start=0.4 stop=0.9 step=0.02
save Q1:ic Q1:ib
"""
    
    # ============================================================================
    # DIODE TESTBENCHES
    # ============================================================================
    
    def _generate_diode_test(self, config: TestbenchConfig) -> str:
        """Generate I-V curve for diode"""
        if config.format == 'ngspice':
            return """* Diode I-V Verification Test
.include {{lib_file}}

Vd d 0 DC 0.7
D1 d 0 {config.device_name}

.control
dc Vd 0 1.0 0.02
let Id = -i(Vd)
let Rd = deriv(Vd)/deriv(Id)

print Id Rd > diode_metrics.txt
quit
.endc
.end
"""
        elif config.format == 'hspice':
            return """* Diode I-V Verification Test
.include {{lib_file}}

Vd d 0 DC 0.7
D1 d 0 {config.device_name}

.dc Vd 0 1.0 0.02
.measure dc Id_07 find i(Vd) at=0.7
.measure dc Rs_07 param='deriv(v(d))/deriv(i(Vd))' at=0.7
.print dc i(Vd)
.end
"""
        else:  # spectre
            return """// Diode I-V Verification Test
include "{{lib_file}}"

Vd (d 0) vsource dc=0.7
D1 (d 0) {config.device_name}

dc dc dev=Vd start=0 stop=1.0 step=0.02
save D1:id
"""
    
    # ============================================================================
    # RESISTOR TESTBENCHES
    # ============================================================================
    
    def _generate_resistor_test(self, config: TestbenchConfig) -> str:
        """Generate DC resistance test"""
        if config.format == 'ngspice':
            return """* Resistor Verification Test
.include {{lib_file}}

Vtest v 0 DC 1.0
R1 v 0 1k {config.device_name} w=1u l=10u

.control
op
let R = v(v)/i(Vtest)

print R > res_metrics.txt
quit
.endc
.end
"""
        elif config.format == 'hspice':
            return """* Resistor Verification Test
.include {{lib_file}}

Vtest v 0 DC 1.0
R1 v 0 1k {config.device_name} w=1u l=10u

.op
.measure dc R_eff param='v(v)/i(Vtest)'
.print dc i(Vtest)
.end
"""
        else:  # spectre
            return """// Resistor Verification Test
include "{{lib_file}}"

Vtest (v 0) vsource dc=1.0
XR1 (v 0) {config.device_name} w=1u l=10u

dc dc
save XR1:*
"""


def generate_testbench(device_class: str, device_name: str, format: str, **kwargs) -> str:
    """
    Convenience function for quick testbench generation
    
    Args:
        device_class: 'capacitor', 'mos', 'bjt', 'diode', 'resistor'
        device_name: Model or subcircuit name
        format: 'ngspice', 'hspice', 'spectre'
        **kwargs: Additional config (mc_runs, area, width, etc.)
    
    Returns:
        Testbench netlist string
    """
    device_enum = DeviceClass(device_class.lower())
    config = TestbenchConfig(
        device_name=device_name,
        device_class=device_enum,
        format=format,
        **kwargs
    )
    
    generator = TestbenchGenerator()
    return generator.generate(config)
