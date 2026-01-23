# Parameter Extraction Fix

**Date:** 2026-01-23  
**Issue:** Parameters not extracted from inline model declarations  
**File:** `gpdk090_capacitor.scs`  
**Root Cause:** Parser regex only matches braced models, not inline parameters

---

## Problem Diagnosis

### The Actual File Format

**Line 48 in gpdk090_capacitor.scs:**
```spectre
model gpdk090_mimcap_x capacitor cj=(1-2m*pc_mc*geo_fac)*cap_var*1e-3 cjsw=(1-2m*pc_mc*geo_fac)*1e-10 tc2=-0.008e-6 tc1=-13e-6
```

This is an **inline model** with parameters on the same line.

### Current Parser Regex

**File:** `src/parsers/spectre_parser.py` line ~195

```python
match = re.match(r"model\s+(\w+)\s+(\w+)\s*\{?", header)
```

**What it matches:**
- ✅ `model nch bsim4 {` (with brace)
- ✅ `model nch bsim4` (without brace)

**What it captures:**
- Group 1: `nch` (name)
- Group 2: `bsim4` (type)
- **❌ Parameters after type are IGNORED**

### Why Parameters Are Lost

**Current flow:**
1. Regex matches `model gpdk090_mimcap_x capacitor`
2. Stops at `cj=...` (not part of pattern)
3. Looks for `{` to start parameter block
4. No `{` found → `param_lines = []` (empty)
5. Returns model with NO parameters

---

## Solution Design

### Approach: Support Both Formats

Spectre has **two model syntax forms:**

#### Format 1: Inline Parameters (THIS FILE)
```spectre
model <name> <type> param1=val1 param2=val2 ...
```

#### Format 2: Braced Parameters (OTHER FILES)
```spectre
model <name> <type> {
  param1=val1
  param2=val2
}
```

**We need to handle BOTH!**

---

## Implementation Plan

### Step 1: Detect Model Format

```python
def _extract_single_block(...):
    header = lines[start].strip()
    
    # Parse: model <name> <type> [params or {]
    match = re.match(r"model\s+(\w+)\s+(\w+)\s*(.*)", header)
    
    name = match.group(1)  # gpdk090_mimcap_x
    model_type = match.group(2)  # capacitor
    remainder = match.group(3)  # cj=... cjsw=... OR {
    
    if remainder.startswith("{"):
        # Braced format
        return _parse_braced_model(...)
    else:
        # Inline format
        return _parse_inline_model(name, model_type, remainder)
```

### Step 2: Parse Inline Parameters

```python
def _parse_inline_model(name, model_type, param_string, section, start):
    """Parse model with inline parameters on same line."""
    
    # param_string = "cj=1e-3 cjsw=1e-10 tc1=-13e-6"
    param_lines = [param_string] if param_string else []
    
    return {
        "name": name,
        "type": model_type,
        "param_lines": param_lines,
        "section": section,
        "start_line": start,
        "end_line": start + 1,
    }
```

### Step 3: Handle Complex Expressions

The parameters contain expressions:
```spectre
cj=(1-2m*pc_mc*geo_fac)*cap_var*1e-3
```

**Current parser behavior:**
- Regex: `(\w+)\s*=\s*([^\s]+)`
- Captures: `cj` = `(1-2m*pc_mc*geo_fac)*cap_var*1e-3` ✓

This should work! But let's verify...

**Wait! The regex `[^\s]+` stops at whitespace!**

Problem:
```
Input: cj=(1-2m*pc_mc*geo_fac)*cap_var*1e-3 cjsw=...
Regex [^\s]+ captures: cj=(1-2m*pc_mc*geo_fac)*cap_var*1e-3
                              ✓ (no spaces, works!)
```

Actually this is fine for this file.

### Step 4: Better Parameter Regex

Current: `(\w+)\s*=\s*([^\s]+)`

Issues:
- Breaks on parameters with spaces (rare but possible)
- Doesn't handle quoted strings

Better regex:
```python
# Match: param=value where value extends until next param= or end
pattern = r'(\w+)\s*=\s*([^\s]+(?:\s+(?!\w+=)[^\s]+)*)'
```

Or simpler: **tokenize by looking ahead for next `\w+=`**

```python
import re

def parse_param_string(s):
    """
    Parse 'a=1 b=2 c=hello world d=3' 
    → {'a':'1', 'b':'2', 'c':'hello world', 'd':'3'}
    """
    params = {}
    # Split by param= pattern but keep the param name
    parts = re.split(r'\s+(?=\w+=)', s)
    for part in parts:
        if '=' in part:
            key, val = part.split('=', 1)
            params[key.strip()] = val.strip()
    return params
```

---

## Implementation

### File: `src/parsers/spectre_parser.py`

**Replace `_extract_single_block` method:**

```python
def _extract_single_block(
    self,
    lines: List[str],
    start: int,
    section: Optional[str],
) -> Optional[Dict[str, Any]]:
    """
    Extract single model block with parameters.
    
    Supports two formats:
    1. Inline: model name type param1=val1 param2=val2
    2. Braced: model name type { params }
    """
    header = lines[start].strip()
    
    # Remove inline comments
    if "//" in header:
        header = header.split("//")[0].strip()
    
    # Match: model <name> <type> <rest>
    match = re.match(r"model\s+(\w+)\s+(\w+)\s*(.*)", header)
    
    if not match:
        logger.debug(f"Invalid model header at line {start}: {header}")
        return None
    
    name = match.group(1)
    model_type = match.group(2)
    remainder = match.group(3).strip()
    
    # Determine format
    if remainder.startswith("{"):
        # Braced format - existing logic
        return self._extract_braced_model(
            lines, start, name, model_type, section
        )
    else:
        # Inline format - NEW
        return self._extract_inline_model(
            name, model_type, remainder, section, start
        )

def _extract_inline_model(
    self,
    name: str,
    model_type: str,
    param_string: str,
    section: Optional[str],
    start: int,
) -> Dict[str, Any]:
    """Extract model with inline parameters on single line."""
    param_lines = [param_string] if param_string else []
    
    return {
        "name": name,
        "type": model_type,
        "param_lines": param_lines,
        "section": section,
        "start_line": start,
        "end_line": start + 1,
    }

def _extract_braced_model(
    self,
    lines: List[str],
    start: int,
    name: str,
    model_type: str,
    section: Optional[str],
) -> Dict[str, Any]:
    """Extract model with braced parameters (existing logic)."""
    # This is the current _extract_single_block logic
    # for handling { ... } blocks
    # (Move existing brace-counting code here)
    ...
```

---

## Testing

### Test Case 1: Inline Model (gpdk090_capacitor.scs)

**Input:**
```spectre
model gpdk090_mimcap_x capacitor cj=1e-3 cjsw=1e-10 tc1=-13e-6
```

**Expected Output:**
```python
{
    "name": "gpdk090_mimcap_x",
    "type": "capacitor",
    "param_lines": ["cj=1e-3 cjsw=1e-10 tc1=-13e-6"],
    "section": "cap",
    "start_line": 48,
    "end_line": 49
}
```

**After `_parse_parameters()`:**
```python
{
    "cj": "1e-3",    # or evaluated to 0.001
    "cjsw": "1e-10",
    "tc1": "-13e-6"
}
```

### Test Case 2: Braced Model (should still work)

**Input:**
```spectre
model nch bsim4 {
  vth0=0.4
  tox=2e-9
}
```

**Expected:** Same as before (no regression)

---

## Expected Results After Fix

### Command:
```bash
python3 -m src.main info tools/spice-libraries/private-models/cadence90/spectre/gpdk090_capacitor.scs --format spectre
```

### Before Fix:
```
Parameters: 0  ← WRONG
```

### After Fix:
```
Parameters: 4  ← CORRECT (cj, cjsw, tc1, tc2)

Parameter Details:
  cj: (1-2m*pc_mc*geo_fac)*cap_var*1e-3
  cjsw: (1-2m*pc_mc*geo_fac)*1e-10
  tc1: -13e-6
  tc2: -0.008e-6
```

### Translation Output:
```spice
* Generated by SPICE Translator
*
.model gpdk090_mimcap_x capacitor cj=1e-3 cjsw=1e-10 tc1=-13e-6 tc2=-0.008e-6
```

Much better! (Though expressions might be simplified)

---

## Implementation Priority

**P0 - CRITICAL:** This fix is essential for usable output files

**Estimated Time:** 30-60 minutes

**Files to Modify:**
1. `src/parsers/spectre_parser.py` (~50 lines changed)

**Testing:**
1. Run on gpdk090_capacitor.scs
2. Verify parameters extracted
3. Check output file has parameters
4. Roundtrip test

---

## Next Steps After This Fix

1. ✅ Extract inline parameters
2. ⚠️ Extract subcircuits (inline subckt)
3. ⚠️ Extract section corners
4. ⚠️ Preserve parametric expressions (don't evaluate)

