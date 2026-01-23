#!/usr/bin/env python3
import subprocess
import tempfile
import os
from pathlib import Path
import math

BASE_DIR = Path(__file__).resolve().parents[1]
LIB_PATH = BASE_DIR / 'output' / 'ngspice' / 'gpdk090_capacitor.lib'

NETLIST_TEMPLATE = """* Numeric validation of lowered capacitor
.include {lib}

* AC source to measure admittance
Vac n 0 ac 1

* Instantiate capacitor subcircuit
Xcap n 0 gpdk090_mimcap area={area} perim={perim} mc_en={mc_en}

.ac lin 1 {freq} {freq}
.print ac i(Vac)
.end
"""


def run_ngspice(netlist_text: str):
    with tempfile.TemporaryDirectory() as td:
        net = Path(td) / 'test.cir'
        log = Path(td) / 'out.log'
        net.write_text(netlist_text)
        # Run ngspice in batch mode
        res = subprocess.run(['ngspice', '-b', '-o', str(log), str(net)], capture_output=True)
        if res.returncode != 0:
            raise RuntimeError(f'ngspice failed: {res.stderr.decode()}')
        out = log.read_text()
        return out


def parse_current_imag(out: str):
    """
    Parse imaginary part of the AC current through the source.
    ngspice prints a table with a column header like 'vac#branch', and rows:
        Index  frequency  vac#branch
        0      1.0e+06    -2.87e-14, -1.69e-07
    We extract the imag component from the first data row.
    """
    import re
    lines = [l.rstrip() for l in out.splitlines()]
    pattern = re.compile(r"^\s*\d+\s+([0-9eE\+\-\.]+)\s+([0-9eE\+\-\.]+),\s+([0-9eE\+\-\.]+)")
    for l in lines:
        m = pattern.match(l)
        if m:
            # freq = float(m.group(1))  # not used
            # real = float(m.group(2))  # not used
            imag = float(m.group(3))
            return imag
    # As a fallback, try to find any 'a,b' pair
    for l in lines:
        if ',' in l:
            try:
                seg = l.split(',')[1].strip()
                imag = float(seg.split()[0])
                return imag
            except Exception:
                continue
    raise ValueError('Could not parse AC current imaginary component')


def expected_cap(area: float, perim: float, cap_var: float = 1.0, geo_fac: float = None, mismatch: float = 1.0):
    # From lowered expressions: C_total = cap_var*(1e-3*area + 1e-10*perim)*mismatch
    return cap_var * ((1e-3 * area) + (1e-10 * perim)) * mismatch


def compute_geo_fac(area: float):
    # geo_fac=1/sqrt(sqrt(area/5e-6/5e-6))
    return 1.0 / math.sqrt(math.sqrt(area / (5e-6 * 5e-6)))


def main():
    assert LIB_PATH.exists(), f'Library not found: {LIB_PATH}'
    freq = 1e6
    tests = [
        {'name': 'Nominal geometry, MC off', 'area': 5e-6 * 5e-6, 'perim': 2 * (5e-6 + 5e-6), 'mc_en': 0},
        {'name': 'Double area, MC off', 'area': 2 * (5e-6 * 5e-6), 'perim': 2 * (5e-6 + 5e-6), 'mc_en': 0},
        {'name': 'Nominal geometry, MC on', 'area': 5e-6 * 5e-6, 'perim': 2 * (5e-6 + 5e-6), 'mc_en': 1},
    ]

    results = []
    for t in tests:
        netlist = NETLIST_TEMPLATE.format(lib=str(LIB_PATH), area=t['area'], perim=t['perim'], mc_en=t['mc_en'], freq=freq)
        out = run_ngspice(netlist)
        try:
            imag = parse_current_imag(out)
        except Exception:
            # Dump log for debugging
            print('--- ngspice log start ---')
            print(out)
            print('--- ngspice log end ---')
            raise
        measured_c = abs(imag) / (2 * math.pi * freq)
        # Expected (without random mismatch when mc_en=1; we compare geometry-only expectation)
        geo_fac = compute_geo_fac(t['area'])
        expected = expected_cap(t['area'], t['perim'], mismatch=1.0)  # ignore randomness for comparison
        results.append({
            'name': t['name'],
            'measured_F': measured_c,
            'expected_F': expected,
            'ratio': measured_c / expected if expected > 0 else float('nan'),
            'raw': out.splitlines()[-10:]
        })

    report_lines = [
        'CAPACITOR NUMERIC VALIDATION (ngspice)',
        f'Library: {LIB_PATH}',
        f'Frequency: {freq} Hz',
        '',
    ]
    for r in results:
        report_lines.append(f"- {r['name']}: measured={r['measured_F']:.6e} F, expected={r['expected_F']:.6e} F, ratio={r['ratio']:.3f}")
    print('\n'.join(report_lines))

if __name__ == '__main__':
    main()
