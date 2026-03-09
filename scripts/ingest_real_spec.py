from __future__ import annotations

from pathlib import Path

from common import write_json, write_text
from docx_3gpp import (
    REAL_RAW_DIR,
    REAL_SLICE_DIR,
    SPEC_ARCHIVE_PATH,
    ensure_real_dirs,
    extract_target_slices,
    load_spec_paragraphs,
    render_markdown,
)


ROOT = Path(__file__).resolve().parents[1]
REAL_REPORT_DIR = ROOT / "outputs" / "reports_real"
RAW_MARKDOWN_PATH = REAL_RAW_DIR / "ts-38.331-v17.6.0.md"


def main() -> None:
    ensure_real_dirs()
    REAL_REPORT_DIR.mkdir(parents=True, exist_ok=True)

    paragraphs = load_spec_paragraphs()
    write_text(RAW_MARKDOWN_PATH, render_markdown(paragraphs))

    slices = extract_target_slices(paragraphs)
    created: list[str] = []
    for procedure_id, content in slices.items():
        header = content.splitlines()[0].removeprefix("## ").strip()
        slug = header.split(" ", 1)[0]
        if procedure_id == slug:
            title = header
        else:
            title = header
        file_name = title.lower().replace(" ", "-")
        path = REAL_SLICE_DIR / f"{file_name}.md"
        write_text(path, content)
        created.append(path.name)

    write_json(
        REAL_REPORT_DIR / "real_ingest.json",
        {
            "source_archive": SPEC_ARCHIVE_PATH.name,
            "paragraph_count": len(paragraphs),
            "raw_markdown": RAW_MARKDOWN_PATH.name,
            "slice_count": len(created),
            "slices": sorted(created),
            "pass": len(created) == 3,
        },
    )
    print(f"ingested real 38.331 spec into {RAW_MARKDOWN_PATH} and created {len(created)} slices")


if __name__ == "__main__":
    main()
