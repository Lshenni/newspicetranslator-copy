#!/usr/bin/env python3
"""Batch rerun + compare for private-model libraries.

Goal:
- Translate inputs under tools/spice-libraries/private-models/ across chosen targets.
- Compare source IR vs. translated IR (structural + parameter retention signals).
- For ngspice targets, optionally run an ngspice smoke simulation using the
  verification testbench generator.

This is intentionally pragmatic: without licensed Spectre/HSPICE simulators,
we cannot guarantee full electrical equivalence; we instead provide:
- IR-level retention checks (names, types, keys, numeric closeness when possible)
- ngspice runtime acceptance checks (translate + parse + simulate)

Usage examples:
  python tools/rerun_private_models.py --targets ngspice --simulate-ngspice
  python tools/rerun_private_models.py --pdks cadence90 smic180HV --targets ngspice hspice
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
import re

# Ensure project root on path when invoked as a script
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in os.sys.path:
    os.sys.path.insert(0, str(BASE_DIR))

from src.main import TranslationEngine
from src.ir.model_ir import ModelIR, DeviceType
from src.parsers import SpectreParser, HSPICEParser, NgspiceParser
from verification.testbench_generator import TestbenchGenerator, TestbenchConfig, DeviceClass
from simulators.run_simulator import run_simulation


SUPPORTED_EXTS = {
    ".scs": "spectre",
    ".sp": "hspice",
    ".spi": "hspice",
    ".mdl": "hspice",
    ".lib": None,  # ambiguous; infer from path
    ".cir": "ngspice",
}


def _infer_format_from_path(path: Path) -> Optional[str]:
    p = str(path).lower()
    if "/spectre/" in p:
        return "spectre"
    if "/hspice/" in p:
        return "hspice"
    if "/ngspice/" in p:
        return "ngspice"
    return None


def detect_source_format(path: Path) -> Optional[str]:
    ext = path.suffix.lower()
    fmt = SUPPORTED_EXTS.get(ext)
    if fmt:
        return fmt
    # infer for ambiguous/unknown extensions
    inferred = _infer_format_from_path(path)
    if inferred:
        return inferred
    # fallback heuristic: .lib defaults to hspice (common for model decks)
    if ext == ".lib":
        return "hspice"
    return None


def parser_for_format(fmt: str):
    if fmt == "spectre":
        return SpectreParser
    if fmt == "hspice":
        return HSPICEParser
    if fmt == "ngspice":
        return NgspiceParser
    raise ValueError(f"Unsupported format: {fmt}")


def extension_for_target(fmt: str) -> str:
    return {"spectre": ".scs", "hspice": ".sp", "ngspice": ".lib"}[fmt]


def normalize_scalar(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v).strip()
    # Strip outer quotes
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
        s = s[1:-1].strip()
    # Strip ngspice braces
    if len(s) >= 2 and s[0] == "{" and s[-1] == "}":
        s = s[1:-1].strip()
    # Collapse whitespace
    s = " ".join(s.split())
    return s


def try_float(v: Any) -> Optional[float]:
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = normalize_scalar(v)
        try:
            return float(s)
        except ValueError:
            return None
    return None


def device_class_for_device_type(dt: DeviceType) -> Optional[DeviceClass]:
    if dt in (DeviceType.NMOS, DeviceType.PMOS):
        return DeviceClass.MOS
    if dt in (DeviceType.NPN, DeviceType.PNP):
        return DeviceClass.BJT
    if dt == DeviceType.DIODE:
        return DeviceClass.DIODE
    if dt == DeviceType.RESISTOR:
        return DeviceClass.RESISTOR
    if dt == DeviceType.CAPACITOR:
        return DeviceClass.CAPACITOR
    return None


@dataclass
class ModelCompareSummary:
    model_name: str
    device_type_src: str
    device_type_tgt: str
    missing_keys: List[str]
    extra_keys: List[str]
    numeric_mismatches: List[str]


@dataclass
class FileRunResult:
    input_file: str
    source_format: str
    target_format: str
    output_file: str
    translated_ok: bool
    parse_ok: bool
    model_count_src: int
    model_count_tgt: int
    model_names_missing: List[str]
    model_names_extra: List[str]
    models_compared: int
    models_with_diffs: int
    ngspice_simulated: bool
    ngspice_sim_ok: Optional[bool]
    ngspice_sim_status: Optional[str]
    ngspice_sim_model: Optional[str]
    ngspice_sim_mos_level: Optional[int]
    ngspice_sim_skip_reason: Optional[str]
    ngspice_sim_log: Optional[str]
    errors: List[str]


def _ngspice_combined_text(sim_result: Any) -> str:
    """Return combined ngspice output text for error classification."""
    return "\n".join(
        [
            sim_result.error_message or "",
            sim_result.stdout or "",
            sim_result.stderr or "",
        ]
    )


def _ngspice_is_unsupported_mos_level(sim_result: Any) -> bool:
    """Detect ngspice 'unsupported MOS device level' failures from logs."""
    # ngspice emits (varies slightly by build):
    # "Only MOS device levels 1-6,8-10,... are supported in this binary"
    text = _ngspice_combined_text(sim_result).lower()
    return "only mos device levels" in text and "supported in this binary" in text


def _extract_model_level_from_deck(deck_path: Path, model_name: str) -> Optional[int]:
    """Extract the integer `level=` value from a `.model <model_name>` card."""
    if not model_name:
        return None
    try:
        lines = deck_path.read_text(errors="replace").splitlines()
    except Exception:
        return None

    # Collect a `.model <name> ...` logical line including `+` continuations.
    model_re = re.compile(rf"^\s*\.model\s+{re.escape(model_name)}\b", flags=re.IGNORECASE)
    i = 0
    while i < len(lines):
        if not model_re.search(lines[i]):
            i += 1
            continue
        parts = [lines[i].strip()]
        j = i + 1
        while j < len(lines) and re.match(r"^\s*\+", lines[j]):
            parts.append(re.sub(r"^\s*\+\s*", "", lines[j]).strip())
            j += 1
        logical = " ".join(parts)
        m = re.search(r"\blevel\s*=\s*\{?\s*([0-9]+)\s*\}?", logical, flags=re.IGNORECASE)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                return None
        return None
    return None


def compare_models(src_models: List[ModelIR], tgt_models: List[ModelIR]) -> Tuple[
    List[str], List[str], List[ModelCompareSummary]
]:
    src_by = {m.name: m for m in src_models}
    tgt_by = {m.name: m for m in tgt_models}

    missing_names = sorted(set(src_by) - set(tgt_by))
    extra_names = sorted(set(tgt_by) - set(src_by))

    summaries: List[ModelCompareSummary] = []
    for name in sorted(set(src_by) & set(tgt_by)):
        sm = src_by[name]
        tm = tgt_by[name]

        sp = sm.base_parameters or {}
        tp = tm.base_parameters or {}

        missing_keys = sorted(set(sp) - set(tp))
        extra_keys = sorted(set(tp) - set(sp))

        numeric_mismatches: List[str] = []
        for k in sorted(set(sp) & set(tp)):
            a = try_float(sp[k])
            b = try_float(tp[k])
            if a is None or b is None:
                continue
            # relative tolerance; keep generous due to formatting differences
            denom = max(1.0, abs(a), abs(b))
            if abs(a - b) / denom > 1e-9:
                numeric_mismatches.append(k)

        if (
            sm.device_type != tm.device_type
            or missing_keys
            or extra_keys
            or numeric_mismatches
        ):
            summaries.append(
                ModelCompareSummary(
                    model_name=name,
                    device_type_src=sm.device_type.value,
                    device_type_tgt=tm.device_type.value,
                    missing_keys=missing_keys,
                    extra_keys=extra_keys,
                    numeric_mismatches=numeric_mismatches,
                )
            )

    return missing_names, extra_names, summaries


def choose_ngspice_smoke_model(models: List[ModelIR]) -> Optional[ModelIR]:
    # Prefer MOS/BJT/Diode since they stress expression evaluation and device code.
    priority = [DeviceType.NMOS, DeviceType.PMOS, DeviceType.NPN, DeviceType.PNP, DeviceType.DIODE]
    by_type: Dict[DeviceType, List[ModelIR]] = {}
    for m in models:
        by_type.setdefault(m.device_type, []).append(m)

    for dt in priority:
        if by_type.get(dt):
            return sorted(by_type[dt], key=lambda x: x.name)[0]

    # fallback: any non-subcircuit
    for m in sorted(models, key=lambda x: x.name):
        if m.device_type != DeviceType.SUBCIRCUIT:
            return m
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Batch rerun + compare for private-models")
    ap.add_argument(
        "--root",
        default=str(BASE_DIR / "tools" / "spice-libraries" / "private-models"),
        help="Root folder to scan for input libraries",
    )
    ap.add_argument(
        "--pdks",
        nargs="*",
        default=[],
        help="Restrict to specific PDK folders under private-models (e.g. cadence90 smic180HV)",
    )
    ap.add_argument(
        "--targets",
        nargs="+",
        default=["ngspice"],
        choices=["spectre", "hspice", "ngspice"],
        help="Target formats to generate",
    )
    ap.add_argument(
        "--max-files",
        type=int,
        default=0,
        help="Limit number of input files (0 = no limit)",
    )
    ap.add_argument(
        "--simulate-ngspice",
        action="store_true",
        help="For ngspice outputs: run one smoke simulation per file",
    )
    ap.add_argument(
        "--output-dir",
        default=str(BASE_DIR / "output" / "private_models_rerun"),
        help="Where to write translated outputs and reports",
    )
    ap.add_argument("--fail-fast", action="store_true", help="Stop on first failure")

    args = ap.parse_args()

    root = Path(args.root)
    out_root = Path(args.output_dir)
    out_root.mkdir(parents=True, exist_ok=True)

    # Gather inputs
    patterns = ["*.scs", "*.sp", "*.spi", "*.mdl", "*.lib", "*.cir"]
    inputs: List[Path] = []
    for p in patterns:
        inputs.extend(root.rglob(p))

    inputs = [p for p in inputs if p.is_file()]
    inputs.sort()

    if args.pdks:
        allowed = {p.lower() for p in args.pdks}

        def _pdk_of(path: Path) -> str:
            try:
                rel = path.relative_to(root)
                return rel.parts[0].lower()
            except Exception:
                return ""

        inputs = [p for p in inputs if _pdk_of(p) in allowed]

    if args.max_files and len(inputs) > args.max_files:
        inputs = inputs[: args.max_files]

    engine = TranslationEngine()
    tbgen = TestbenchGenerator()

    results: List[FileRunResult] = []

    for in_file in inputs:
        source_fmt = detect_source_format(in_file)
        if not source_fmt:
            continue

        # Parse source to IR once for comparison
        try:
            src_models = parser_for_format(source_fmt)(in_file).parse_to_ir()
            src_parse_ok = True
        except Exception as e:
            src_models = []
            src_parse_ok = False
            src_parse_err = str(e)

        for tgt_fmt in args.targets:
            if tgt_fmt == source_fmt:
                continue

            out_rel = in_file.relative_to(root)
            pdk = out_rel.parts[0]
            out_dir = out_root / f"{source_fmt}_to_{tgt_fmt}" / pdk / "/".join(out_rel.parts[1:-1])
            out_dir.mkdir(parents=True, exist_ok=True)
            out_file = out_dir / (in_file.stem + extension_for_target(tgt_fmt))

            errors: List[str] = []

            if not src_parse_ok:
                errors.append(f"Source parse failed: {src_parse_err}")

            translated_ok = False
            if src_parse_ok and len(src_models) == 0:
                errors.append("Skipped translation: source parsed 0 models (likely an include aggregator)")
            else:
                try:
                    tr = engine.translate(
                        input_file=in_file,
                        source_format=source_fmt,
                        target_format=tgt_fmt,
                        output_file=out_file,
                        validate=True,
                    )
                    translated_ok = bool(tr.get("success"))
                    if not translated_ok:
                        errors.append(f"Translation failed: {tr.get('error', 'unknown')}")
                except Exception as e:
                    errors.append(f"Translation exception: {e}")

            # Parse translated
            tgt_models: List[ModelIR] = []
            parse_ok = False
            if translated_ok:
                try:
                    tgt_models = parser_for_format(tgt_fmt)(out_file).parse_to_ir()
                    parse_ok = True
                except Exception as e:
                    errors.append(f"Target parse failed: {e}")

            # Compare IRs (best-effort)
            missing_names: List[str] = []
            extra_names: List[str] = []
            diffs: List[ModelCompareSummary] = []
            if src_parse_ok and parse_ok:
                missing_names, extra_names, diffs = compare_models(src_models, tgt_models)

            # ngspice smoke simulation
            ng_simulated = False
            ng_ok: Optional[bool] = None
            ng_status: Optional[str] = None
            ng_model: Optional[str] = None
            ng_mos_level: Optional[int] = None
            ng_skip_reason: Optional[str] = None
            ng_log: Optional[str] = None

            if args.simulate_ngspice and tgt_fmt == "ngspice" and parse_ok:
                candidate = choose_ngspice_smoke_model(tgt_models)
                if candidate:
                    dc = device_class_for_device_type(candidate.device_type)
                    if dc:
                        def _has_subckt(deck_path, subckt_name: str) -> bool:
                            try:
                                import re

                                text = deck_path.read_text(errors="replace")
                                return re.search(
                                    rf"^\s*\.subckt\s+{re.escape(subckt_name)}\b",
                                    text,
                                    flags=re.IGNORECASE | re.MULTILINE,
                                ) is not None
                            except Exception:
                                return False

                        if dc == DeviceClass.CAPACITOR and not _has_subckt(out_file, candidate.name):
                            # Some libraries provide primitive capacitor models (.model <name> C ...)
                            # rather than subckt wrappers. Use a C element in that case.
                            netlist = """* Capacitor Model AC Smoke Test
.include {lib_file}

Vac P 0 AC 1
C1 P 0 {model_name} c=1p

.control
ac dec 10 1 1G
quit
.endc
.end
""".replace("{model_name}", candidate.name)
                            netlist = netlist.replace("{lib_file}", f'"{out_file.resolve()}"')
                        else:
                            cfg = TestbenchConfig(
                                device_name=candidate.name,
                                device_class=dc,
                                format="ngspice",
                            )
                            netlist = tbgen.generate(cfg)
                            netlist = netlist.replace("{lib_file}", f'"{out_file.resolve()}"')

                        sim_dir = out_root / "ngspice_smoke" / pdk / out_file.stem
                        sim_dir.mkdir(parents=True, exist_ok=True)

                        sim = run_simulation(netlist, "ngspice", sim_dir)

                        # Fallback: some translated Spectre libraries place `.model` cards
                        # inside `.subckt` blocks (local scope). If we pick such a model for
                        # a primitive Q/D/M instance in the testbench, ngspice can't resolve it.
                        # In that case, try a generic subckt instantiation smoke test.
                        def _maybe_subckt_fallback(sim_result):
                            err_text = "\n".join(
                                [sim_result.error_message or "", sim_result.stderr or "", sim_result.stdout or ""]
                            ).lower()
                            if "can't find model" not in err_text and "cannot find model" not in err_text:
                                return None

                            try:
                                import re

                                deck_text = out_file.read_text(errors="replace")
                                lines = deck_text.splitlines()

                                # Collect subckt blocks: name -> (ports, body_text)
                                subckts = []
                                i = 0
                                while i < len(lines):
                                    m = re.match(r"^\s*\.subckt\s+(\S+)\s*(.*)$", lines[i], flags=re.IGNORECASE)
                                    if not m:
                                        i += 1
                                        continue
                                    name = m.group(1)
                                    rest = m.group(2).strip()
                                    tokens = rest.split() if rest else []
                                    ports = []
                                    for t in tokens:
                                        if "=" in t:
                                            break
                                        ports.append(t)
                                    body = []
                                    i += 1
                                    while i < len(lines) and not re.match(r"^\s*\.ends\b", lines[i], flags=re.IGNORECASE):
                                        body.append(lines[i])
                                        i += 1
                                    subckts.append((name, ports, "\n".join(body)))
                                    i += 1

                                if not subckts:
                                    return None

                                # Prefer a subckt that references the missing model name.
                                missing = (candidate.name or "").lower()
                                chosen = None
                                for name, ports, body in subckts:
                                    if missing and missing in body.lower():
                                        chosen = (name, ports)
                                        break
                                if chosen is None:
                                    chosen = (subckts[0][0], subckts[0][1])

                                subckt_name, ports = chosen
                                if not ports:
                                    return None

                                # Tie each port node to 0V to avoid floating nodes.
                                node_names = [f"n{i+1}" for i in range(len(ports))]
                                vsources = "\n".join([f"V{i+1} {n} 0 0" for i, n in enumerate(node_names)])
                                inst = f"XU1 {' '.join(node_names)} {subckt_name}"

                                fb = """* Subckt Smoke Test (fallback)
.include {lib_file}

{vsources}

{inst}

.op
.end
""".replace("{vsources}", vsources).replace("{inst}", inst)

                                fb = fb.replace("{lib_file}", f'"{out_file.resolve()}"')
                                return fb
                            except Exception:
                                return None

                        fb_netlist = _maybe_subckt_fallback(sim)
                        if fb_netlist is not None:
                            sim = run_simulation(fb_netlist, "ngspice", sim_dir)

                        ng_simulated = True
                        ng_ok = bool(sim.success)
                        ng_status = "passed" if sim.success else "failed"
                        ng_model = candidate.name

                        if not sim.success and _ngspice_is_unsupported_mos_level(sim):
                            # Known limitation of the current ngspice binary; do not count as a
                            # translation failure. Record as skipped with metadata.
                            ng_status = "skipped"
                            ng_skip_reason = "unsupported_mos_level"
                            ng_mos_level = _extract_model_level_from_deck(out_file, candidate.name)
                            ng_ok = None

                        log_path = sim_dir / "ngspice_stdout_stderr.txt"
                        log_path.write_text(
                            "=== STDOUT ===\n" + (sim.stdout or "") + "\n\n=== STDERR ===\n" + (sim.stderr or "")
                        )
                        ng_log = str(log_path)
                        if not sim.success and ng_status != "skipped":
                            errors.append(f"ngspice sim failed: {sim.error_message or 'unknown'}")
                    else:
                        errors.append(f"No supported device_class for device_type={candidate.device_type.value}")
                else:
                    errors.append("No suitable model found for ngspice smoke test")

            res = FileRunResult(
                input_file=str(in_file),
                source_format=source_fmt,
                target_format=tgt_fmt,
                output_file=str(out_file),
                translated_ok=translated_ok,
                parse_ok=parse_ok,
                model_count_src=len(src_models),
                model_count_tgt=len(tgt_models),
                model_names_missing=missing_names[:50],
                model_names_extra=extra_names[:50],
                models_compared=len(set(m.name for m in src_models) & set(m.name for m in tgt_models)),
                models_with_diffs=len(diffs),
                ngspice_simulated=ng_simulated,
                ngspice_sim_ok=ng_ok,
                ngspice_sim_status=ng_status,
                ngspice_sim_model=ng_model,
                ngspice_sim_mos_level=ng_mos_level,
                ngspice_sim_skip_reason=ng_skip_reason,
                ngspice_sim_log=ng_log,
                errors=errors,
            )
            results.append(res)

            if args.fail_fast and (errors or not translated_ok):
                break

        if args.fail_fast and results and results[-1].errors:
            break

    # Write report
    report_json = out_root / "report.json"
    report_md = out_root / "report.md"

    payload = {
        "root": str(root),
        "output_dir": str(out_root),
        "file_count": len(inputs),
        "results": [asdict(r) for r in results],
    }
    report_json.write_text(json.dumps(payload, indent=2))

    # Human summary
    total = len(results)
    ok = sum(1 for r in results if r.translated_ok and r.parse_ok and not r.errors)
    sim_total = sum(1 for r in results if r.ngspice_simulated)
    sim_ok = sum(1 for r in results if r.ngspice_sim_status == "passed")
    sim_skipped = sum(1 for r in results if r.ngspice_sim_status == "skipped")
    sim_failed = sum(1 for r in results if r.ngspice_sim_status == "failed")

    lines = [
        "# Private Models Rerun Report",
        "",
        f"- Inputs scanned: {len(inputs)}",
        f"- Translation targets: {', '.join(args.targets)}",
        f"- Runs recorded: {total}",
        f"- Clean runs (translate+parse, no errors): {ok}",
    ]
    if args.simulate_ngspice:
        lines.append(
            f"- ngspice smoke sims: {sim_ok} passed / {sim_skipped} skipped / {sim_failed} failed (total {sim_total})"
        )

    # Show first N failures
    failures = [r for r in results if r.errors or not r.translated_ok or not r.parse_ok]
    if failures:
        lines += ["", "## First Failures"]
        for r in failures[:20]:
            lines.append(f"- {r.source_format}→{r.target_format}: {r.input_file} → {r.output_file}")
            for e in r.errors[:5]:
                lines.append(f"  - {e}")

    # Show ngspice-known-limitations separately
    skipped = [r for r in results if r.ngspice_sim_status == "skipped"]
    if skipped:
        lines += ["", "## ngspice Skipped (Known Limitations)"]
        for r in skipped[:50]:
            extra = ""
            if r.ngspice_sim_skip_reason:
                extra += f" reason={r.ngspice_sim_skip_reason}"
            if r.ngspice_sim_mos_level is not None:
                extra += f" level={r.ngspice_sim_mos_level}"
            lines.append(
                f"- {r.source_format}→{r.target_format}: {r.input_file} (model {r.ngspice_sim_model}){extra}"
            )

    report_md.write_text("\n".join(lines) + "\n")

    print(f"Wrote: {report_json}")
    print(f"Wrote: {report_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
