#!/usr/bin/env python3
from pathlib import Path
import re

BASE_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = BASE_DIR / 'output' / 'ngspice'
DST_DIR = BASE_DIR / 'output' / 'simready_ngspice'
DST_DIR.mkdir(parents=True, exist_ok=True)

MOS_FILE = SRC_DIR / 'gpdk090_mos.lib'
RES_FILE = SRC_DIR / 'gpdk090_resistor.lib'
DIO_FILE = SRC_DIR / 'gpdk090_diode.lib'


def sanitize_mos(text: str) -> str:
    # Remove problematic '(type=n)' or '(type=p)' in .model lines
    text = re.sub(r"(\.model\s+\S+\s+nm?os)\s*\(type\s*=\s*[npNP]\)\s*", r"\1 ", text)
    text = re.sub(r"(\.model\s+\S+\s+pm?os)\s*\(type\s*=\s*[npNP]\)\s*", r"\1 ", text)
    return text


def sanitize_res(text: str) -> str:
    """
    Sanitize resistor library for ngspice:
    1. Comment out undefined noise model instances (rnoise_va)
    2. Normalize line continuations (backslash -> plus sign)
    3. Add default values for undefined parameters (pres_mc)
    """
    out_lines = []
    in_subckt = False
    for line in text.splitlines():
        # Comment out undefined noise model
        if 'rnoise_va' in line.lower():
            out_lines.append('* ' + line)
            continue
        
        # Normalize backslash continuations to plus sign
        if line.rstrip().endswith('\\'):
            # Replace trailing backslash with nothing, next line will use +
            cleaned = line.rstrip()[:-1].rstrip()
            out_lines.append(cleaned)
        elif in_subckt and line.strip() and not line.strip().startswith('.') and not line.strip().startswith('*'):
            # Continuation line in subckt parameter block
            if '=' in line:
                out_lines.append('+ ' + line.strip())
            else:
                out_lines.append(line)
        else:
            out_lines.append(line)
        
        # Track subcircuit blocks
        if line.strip().lower().startswith('.subckt'):
            in_subckt = True
        elif line.strip().lower().startswith('.ends'):
            in_subckt = False
    
    result = '\n'.join(out_lines) + '\n'
    
    # Add global default for pres_mc if not defined
    if 'pres_mc' in result and '.param pres_mc' not in result.lower():
        result = '.param pres_mc=0\n\n' + result
    
    return result


def sanitize_dio(text: str) -> str:
    # Placeholder: pass-through for now
    return text


def main():
    if MOS_FILE.exists():
        mos_text = MOS_FILE.read_text()
        (DST_DIR / MOS_FILE.name).write_text(sanitize_mos(mos_text))
        print(f"Sanitized MOS -> {(DST_DIR / MOS_FILE.name)}")
    else:
        print("MOS lib not found")
    if RES_FILE.exists():
        res_text = RES_FILE.read_text()
        (DST_DIR / RES_FILE.name).write_text(sanitize_res(res_text))
        print(f"Sanitized RES -> {(DST_DIR / RES_FILE.name)}")
    else:
        print("RES lib not found")
    if DIO_FILE.exists():
        dio_text = DIO_FILE.read_text()
        (DST_DIR / DIO_FILE.name).write_text(sanitize_dio(dio_text))
        print(f"Sanitized DIO -> {(DST_DIR / DIO_FILE.name)}")
    else:
        print("DIO lib not found")

if __name__ == '__main__':
    main()
