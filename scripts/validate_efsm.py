from __future__ import annotations

from pathlib import Path

from common import (
    CORPUS_SLICE_DIR,
    EFSM_OUTPUT_DIR,
    REPORT_OUTPUT_DIR,
    flatten_text,
    list_efsm_files,
    parse_transition_line,
    procedure_index_from_slices,
    read_json,
    write_json,
)

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
TRANSITION_KEYS = {"step", "source_state", "event", "actions", "target_state", "refs"}


def validate_structure(efsm: dict[str, object]) -> list[str]:
    errors: list[str] = []
    missing_top = sorted(TOP_LEVEL_KEYS - set(efsm.keys()))
    if missing_top:
        errors.append(f"missing_top_level_keys={missing_top}")
    for transition in efsm.get("transitions", []):
        missing = sorted(TRANSITION_KEYS - set(transition.keys()))
        if missing:
            errors.append(f"transition_missing_keys={missing}")
        if not transition.get("actions"):
            errors.append(f"transition_{transition.get('step')}_has_no_actions")
    return errors


def validate_against_slice(slice_path: Path, efsm: dict[str, object], procedure_index: dict[str, str]) -> dict[str, object]:
    lines = slice_path.read_text().splitlines()
    raw_transition_lines = [
        parse_transition_line(line)
        for line in lines
        if line.strip().startswith(tuple(str(i) + ">" for i in range(1, 10)))
    ]
    extracted_transitions = efsm["transitions"]
    bullet_alignment = {
        "expected": len(raw_transition_lines),
        "actual": len(extracted_transitions),
        "match": len(raw_transition_lines) == len(extracted_transitions),
    }

    searchable_text = flatten_text(
        [
            *(efsm.get("timers", [])),
            *(efsm.get("messages", [])),
            *(efsm.get("variables", [])),
            *[
                " ".join(
                    [
                        transition.get("source_state", ""),
                        transition.get("event", ""),
                        transition.get("guard") or "",
                        " ".join(transition.get("actions", [])),
                        transition.get("target_state", ""),
                        " ".join(transition.get("refs", [])),
                    ]
                )
                for transition in extracted_transitions
            ],
        ]
    )

    terminology = {}
    for category in ("timers", "messages", "variables"):
        hints = efsm.get(category, [])
        hit = sum(1 for item in hints if item.lower() in searchable_text)
        terminology[category] = {
            "expected": len(hints),
            "matched": hit,
            "coverage": 1.0 if not hints else round(hit / len(hints), 3),
        }

    unresolved_refs: list[str] = []
    for transition in extracted_transitions:
        for ref in transition["refs"]:
            resolved = False
            for procedure_id in procedure_index:
                if ref == procedure_id or ref.startswith(procedure_id + "."):
                    resolved = True
                    break
            if not resolved:
                unresolved_refs.append(ref)

    return {
        "bullet_alignment": bullet_alignment,
        "terminology_coverage": terminology,
        "reference_closure": {
            "unresolved_refs": sorted(set(unresolved_refs)),
            "match": not unresolved_refs,
        },
    }


def main() -> None:
    procedure_index = procedure_index_from_slices()
    for efsm_path in list_efsm_files():
        efsm = read_json(efsm_path)
        slice_path = CORPUS_SLICE_DIR / efsm["source_document"]
        report = {
            "efsm_file": efsm_path.name,
            "structure_errors": validate_structure(efsm),
        }
        report.update(validate_against_slice(slice_path, efsm, procedure_index))
        report["pass"] = (
            not report["structure_errors"]
            and report["bullet_alignment"]["match"]
            and report["reference_closure"]["match"]
        )
        report_path = REPORT_OUTPUT_DIR / efsm_path.name
        write_json(report_path, report)
    print(f"validated {len(list_efsm_files())} EFSM files into {REPORT_OUTPUT_DIR}")


if __name__ == "__main__":
    main()
