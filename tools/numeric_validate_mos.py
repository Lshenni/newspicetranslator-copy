#!/usr/bin/env python3
import re
import subprocess
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
LIB_PATH = BASE_DIR / 'output' / 'simready_ngspice' / 'gpdk090_mos.lib'

MODEL_RE = re.compile(r"^\s*\.model\s+(\S+)\s+(\S+)", re.IGNORECASE)

NETLIST_TMPL = """* Numeric validation of MOS model
.include {lib}

* Bias supplies
Vd d 0 {vd}
Vg g 0 0
Vs s 0 0
Vb b 0 0

* Device under test
M1 d g s b {model} L={L} W={W}

.dc Vg 0 {vgmax} {vgstep}
.print dc i(Vd)
.end
"""


def parse_models(lib_text: str):
    models = []
    for line in lib_text.splitlines():
        m = MODEL_RE.match(line)
        if m:
            name, mtype = m.group(1), m.group(2).lower()
            models.append((name, mtype))
    return models


def run_ngspice(netlist_text: str):
    with tempfile.TemporaryDirectory() as td:
        net = Path(td) / 'mos_test.cir'
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
        # ngspice DC table header includes 'Index   v-sweep   vd#branch'
        if l.lower().startswith('index') and 'vd#branch' in l.lower():
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
    models = parse_models(LIB_PATH.read_text())
    if not models:
        print('No models found in MOS library; cannot run numeric validation.')
        return
    # Pick the first model
    model_name = models[0][0]
    net = NETLIST_TMPL.format(lib=str(LIB_PATH), model=model_name, vd=0.9, L='0.09u', W='1u', vgmax=1.2, vgstep=0.2)
    out = run_ngspice(net)
    currents = parse_currents(out)
    if not currents:
        print('Could not parse drain currents. Log follows:\n')
        print(out)
        return
    print('MOS NUMERIC VALIDATION (ngspice)')
    print(f'Library: {LIB_PATH}')
    print(f'Model: {model_name}')
    print(f'Currents (A) across Vg sweep: {currents}')
    # Basic sanity: drain current magnitude should increase with Vg
    abs_curr = [abs(c) for c in currents]
    increasing_abs = all(abs_curr[i] <= abs_curr[i+1] for i in range(len(abs_curr)-1))
    print(f'Monotonic |Id| increasing: {increasing_abs}')

if __name__ == '__main__':
    main()
