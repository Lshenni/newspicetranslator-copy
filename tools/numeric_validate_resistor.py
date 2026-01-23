#!/usr/bin/env python3
import subprocess
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
LIB_PATH = BASE_DIR / 'output' / 'simready_ngspice' / 'gpdk090_resistor.lib'

NETLIST_TMPL = """* Numeric validation of resistor subcircuit
.include {lib}

* Sweep DC voltage and measure current
V1 PLUS 0 {vmax}
X1 PLUS 0 0 gpdk090_ressndiff l={L} w={W}

.dc V1 0 {vmax} {vstep}
.print dc i(V1)
.end
"""


def run_ngspice(netlist_text: str):
    with tempfile.TemporaryDirectory() as td:
        net = Path(td) / 'res_test.cir'
        log = Path(td) / 'out.log'
        net.write_text(netlist_text)
        res = subprocess.run(['ngspice', '-b', '-o', str(log), str(net)], capture_output=True)
        if res.returncode != 0:
            raise RuntimeError(res.stderr.decode())
        return log.read_text()


def parse_currents(out: str):
    currents = []
    in_table = False
    for line in out.splitlines():
        l = line.strip()
        if l.lower().startswith('index') and 'v1#branch' in l.lower():
            in_table = True
            continue
        if in_table:
            if not l:
                break
            parts = l.split()
            if len(parts) >= 3:
                try:
                    val = float(parts[-1].replace(',', ''))
                    currents.append(val)
                except Exception:
                    continue
    return currents


def main():
    assert LIB_PATH.exists(), f'Library not found: {LIB_PATH}'
    net = NETLIST_TMPL.format(lib=str(LIB_PATH), vmax=1.0, vstep=0.5, L='0.6e-6', W='0.6e-6')
    out = run_ngspice(net)
    currents = parse_currents(out)
    if not currents:
        print('Could not parse resistor currents. Log follows:\n')
        print(out)
        return
    print('RESISTOR NUMERIC VALIDATION (ngspice)')
    print(f'Library: {LIB_PATH}')
    print(f'Currents (A) across V sweep: {currents}')
    # Ohmic behavior: current proportional to voltage -> non-decreasing with V
    nondecreasing = all(currents[i] <= currents[i+1] for i in range(len(currents)-1))
    print(f'Monotonic I(V) non-decreasing: {nondecreasing}')

if __name__ == '__main__':
    main()
