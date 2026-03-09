from __future__ import annotations

from pathlib import Path
import re

from common import flatten_text, read_json, write_json


ROOT = Path(__file__).resolve().parents[1]
REAL_SLICE_DIR = ROOT / "corpus" / "real" / "slices"
REAL_EFSM_DIR = ROOT / "outputs" / "efsm_real"
REAL_REPORT_DIR = ROOT / "outputs" / "reports_real"

TOP_LEVEL_KEYS = {
    "spec",
    "release",
    "source_document",
    "procedure",
    "messages",
    "timers",
    "variables",
    "transitions",
}
TRANSITION_KEYS = {"step", "source_state", "event", "guard", "actions", "target_state", "refs"}
REF_RE = re.compile(r"^\d+(?:\.\d+)+(?:[a-z])?$")


def validate_structure(efsm: dict[str, object]) -> list[str]:
    errors: list[str] = []
    missing_top = sorted(TOP_LEVEL_KEYS - set(efsm.keys()))
    if missing_top:
        errors.append(f"missing_top_level_keys={missing_top}")
    if not efsm.get("transitions"):
        errors.append("empty_transitions")
    for transition in efsm.get("transitions", []):
        missing = sorted(TRANSITION_KEYS - set(transition.keys()))
        if missing:
            errors.append(f"transition_missing_keys={missing}")
        if not transition.get("actions"):
            errors.append(f"transition_{transition.get('step')}_has_no_actions")
        if not transition.get("refs"):
            errors.append(f"transition_{transition.get('step')}_has_no_refs")
    return errors


def term_present(term: str, source_text: str) -> bool:
    variants = {
        term.lower(),
        term.lower().replace("_", "-"),
        term.lower().replace("_", " "),
        term.lower().replace("-", " "),
    }
    return any(variant in source_text for variant in variants)


def coverage_report(category: str, values: list[str], source_text: str) -> dict[str, object]:
    matched = [value for value in values if term_present(value, source_text)]
    return {
        "category": category,
        "expected": len(values),
        "matched": len(matched),
        "coverage": 1.0 if not values else round(len(matched) / len(values), 3),
        "missing": [value for value in values if value not in matched],
    }


def main() -> None:
    REAL_REPORT_DIR.mkdir(parents=True, exist_ok=True)

    for efsm_path in sorted(REAL_EFSM_DIR.glob("*.json")):
        efsm = read_json(efsm_path)
        slice_path = REAL_SLICE_DIR / efsm["source_document"]
        source_text = flatten_text(slice_path.read_text().splitlines())
        transitions = efsm["transitions"]

        step_sequence = [transition["step"] for transition in transitions]
        step_sequence_report = {
            "expected": list(range(1, len(step_sequence) + 1)),
            "actual": step_sequence,
            "match": step_sequence == list(range(1, len(step_sequence) + 1)),
        }
        ref_report = {
            "invalid": sorted(
                {
                    ref
                    for transition in transitions
                    for ref in transition["refs"]
                    if not REF_RE.match(ref)
                }
            ),
        }
        ref_report["match"] = not ref_report["invalid"]

        report = {
            "efsm_file": efsm_path.name,
            "structure_errors": validate_structure(efsm),
            "step_sequence": step_sequence_report,
            "messages": coverage_report("messages", efsm["messages"], source_text),
            "timers": coverage_report("timers", efsm["timers"], source_text),
            "variables": coverage_report("variables", efsm["variables"], source_text),
            "reference_format": ref_report,
        }
        report["pass"] = (
            not report["structure_errors"]
            and report["step_sequence"]["match"]
            and report["reference_format"]["match"]
            and report["messages"]["coverage"] >= 0.5
            and report["timers"]["coverage"] >= 0.5
        )
        write_json(REAL_REPORT_DIR / efsm_path.name, report)

    print(f"validated {len(list(REAL_EFSM_DIR.glob('*.json')))} real EFSM files into {REAL_REPORT_DIR}")


if __name__ == "__main__":
    main()
