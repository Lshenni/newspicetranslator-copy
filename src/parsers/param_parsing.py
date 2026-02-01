"""Utilities for parsing SPICE parameter strings safely.

These helpers are intentionally conservative: they avoid treating arithmetic
operators (notably '*') as comment delimiters and they preserve quoted
expressions so that writers can round-trip them.

Compliance: CONSTRAINTS.md
"""

from __future__ import annotations

from typing import Dict, Iterator, List, Optional, Tuple


def strip_inline_comment(line: str, markers: Tuple[str, ...] = ("$",)) -> str:
    """Strip inline comments (e.g. '$ ...') while respecting quotes.

    Important: '*' is a multiplication operator in many model expressions.
    If '*' is included in markers, we only treat it as a comment delimiter when
    it appears at the start of a line segment (i.e. at column 0) or is preceded
    by whitespace, and only when outside quotes.

    Args:
        line: Input line
        markers: Comment markers to remove when encountered outside quotes

    Returns:
        Line with the first comment marker (outside quotes) removed.
    """

    in_single = False
    in_double = False

    for idx, ch in enumerate(line):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif not in_single and not in_double and ch in markers:
            if ch == "*":
                if idx == 0 or line[idx - 1].isspace():
                    return line[:idx]
                continue
            return line[:idx]

    return line


def iter_param_assignments(param_str: str) -> Iterator[Tuple[str, str]]:
    """Iterate key/value assignments from a SPICE parameter string.

    Supports patterns like:
      - a=1 b=2
      - a = '1*(1+da)' b=3
      - a="some string" b=4

    The value is returned as the raw substring (trimmed), including surrounding
    quotes if present.

    This parser is quote-aware and uses a lookahead for the next 'name=' token
    to determine where a value ends.
    """

    s = param_str.strip()
    n = len(s)
    i = 0

    def skip_ws(pos: int) -> int:
        while pos < n and s[pos].isspace():
            pos += 1
        return pos

    def is_name_char(c: str) -> bool:
        return c.isalnum() or c == "_"

    while True:
        i = skip_ws(i)
        if i >= n:
            return

        # Read parameter name
        name_start = i
        while i < n and is_name_char(s[i]):
            i += 1
        name = s[name_start:i]
        if not name:
            # Skip unexpected character
            i += 1
            continue

        i = skip_ws(i)
        if i >= n or s[i] != "=":
            # Not an assignment; skip to next whitespace
            while i < n and not s[i].isspace():
                i += 1
            continue

        i += 1  # skip '='
        i = skip_ws(i)

        # Read value until next name= (outside quotes)
        value_start = i
        in_single = False
        in_double = False
        paren_depth = 0

        while i < n:
            ch = s[i]
            if ch == "'" and not in_double:
                in_single = not in_single
            elif ch == '"' and not in_single:
                in_double = not in_double
            elif not in_single and not in_double:
                if ch == "(":
                    paren_depth += 1
                elif ch == ")" and paren_depth > 0:
                    paren_depth -= 1
                elif ch.isspace() and paren_depth == 0:
                    # Lookahead for start of next assignment
                    j = i
                    while j < n and s[j].isspace():
                        j += 1
                    k = j
                    while k < n and is_name_char(s[k]):
                        k += 1
                    k2 = k
                    while k2 < n and s[k2].isspace():
                        k2 += 1
                    if j < k and k2 < n and s[k2] == "=":
                        break
            i += 1

        value = s[value_start:i].strip()
        yield name, value

        # Continue parsing at current i (at whitespace before next name=)


def parse_param_string(param_str: str) -> Dict[str, str]:
    """Parse a SPICE parameter string into a dict of raw strings."""
    out: Dict[str, str] = {}
    for k, v in iter_param_assignments(param_str):
        if k:
            out[k] = v
    return out
