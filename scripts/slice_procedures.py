from __future__ import annotations

from pathlib import Path

from common import CORPUS_RAW_DIR, CORPUS_SLICE_DIR, PROCEDURE_RE, ensure_dirs, slugify_procedure, write_text


def slice_raw_markdown(raw_path: Path) -> list[Path]:
    ensure_dirs()
    created: list[Path] = []
    content = raw_path.read_text().splitlines()
    current_header: str | None = None
    current_lines: list[str] = []
    current_path: Path | None = None

    def flush() -> None:
        nonlocal current_header, current_lines, current_path
        if current_header and current_lines and current_path:
            write_text(current_path, "\n".join(current_lines))
            created.append(current_path)
        current_header = None
        current_lines = []
        current_path = None

    for line in content:
        match = PROCEDURE_RE.match(line)
        if match:
            flush()
            procedure_id = match.group("id")
            title = match.group("title")
            slug = slugify_procedure(procedure_id, title)
            current_header = line
            current_path = CORPUS_SLICE_DIR / f"{slug}.md"
            current_lines = [line]
            continue
        if current_header:
            current_lines.append(line)

    flush()
    return created


def main() -> None:
    raw_files = sorted(CORPUS_RAW_DIR.glob("*.md"))
    created: list[Path] = []
    for raw_file in raw_files:
        created.extend(slice_raw_markdown(raw_file))
    print(f"sliced {len(created)} procedures into {CORPUS_SLICE_DIR}")


if __name__ == "__main__":
    main()
