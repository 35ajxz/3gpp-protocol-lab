from __future__ import annotations

from pathlib import Path

from common import (
    CORPUS_SLICE_DIR,
    EFSM_OUTPUT_DIR,
    PROCEDURE_RE,
    ensure_dirs,
    parse_transition_line,
    slugify_procedure,
    split_csv,
    write_json,
)


def extract_from_slice(path: Path) -> dict[str, object]:
    lines = path.read_text().splitlines()
    header = None
    transitions: list[dict[str, object]] = []
    timers: list[str] = []
    messages: list[str] = []
    variables: list[str] = []

    for line in lines:
        if header is None:
            header = PROCEDURE_RE.match(line)
        if line.strip().startswith(tuple(str(i) + ">" for i in range(1, 10))):
            transitions.append(parse_transition_line(line))
        if line.startswith("- timers:"):
            raw = line.split(":", 1)[1].strip()
            timers = [] if raw == "none" else split_csv(raw)
        if line.startswith("- messages:"):
            messages = split_csv(line.split(":", 1)[1].strip())
        if line.startswith("- variables:"):
            variables = split_csv(line.split(":", 1)[1].strip())

    if header is None:
        raise ValueError(f"Missing procedure header in {path}")

    procedure_id = header.group("id")
    title = header.group("title")
    slug = slugify_procedure(procedure_id, title)
    return {
        "spec": "TS 38.331",
        "release": "Rel-17",
        "source_document": path.name,
        "procedure": {
            "id": procedure_id,
            "title": title,
            "slug": slug,
        },
        "messages": messages,
        "timers": timers,
        "variables": variables,
        "transitions": transitions,
    }


def main() -> None:
    ensure_dirs()
    count = 0
    for slice_path in sorted(CORPUS_SLICE_DIR.glob("*.md")):
        efsm = extract_from_slice(slice_path)
        output_path = EFSM_OUTPUT_DIR / f"{efsm['procedure']['slug']}.json"
        write_json(output_path, efsm)
        count += 1
    print(f"extracted {count} EFSM files into {EFSM_OUTPUT_DIR}")


if __name__ == "__main__":
    main()
