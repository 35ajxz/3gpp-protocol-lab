from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import re
from xml.etree import ElementTree as ET
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
SPEC_ARCHIVE_PATH = ROOT / "vendor" / "3gpp" / "38331-h60.zip"
REAL_RAW_DIR = ROOT / "corpus" / "real" / "raw"
REAL_SLICE_DIR = ROOT / "corpus" / "real" / "slices"

TARGET_PROCEDURE_IDS = ("5.3.3", "5.3.5.11", "5.3.13")

HEADING_STYLE_RE = re.compile(r"heading (?P<level>\d+)")
HEADING_TEXT_RE = re.compile(r"^(?P<id>\d+(?:\.\d+)*(?:[a-z])?)(?P<title>\S.*)$")


@dataclass(frozen=True)
class DocParagraph:
    index: int
    text: str
    style: str

    @property
    def heading_level(self) -> int | None:
        match = HEADING_STYLE_RE.match(self.style)
        if not match:
            return None
        return int(match.group("level"))


def ensure_real_dirs() -> None:
    REAL_RAW_DIR.mkdir(parents=True, exist_ok=True)
    REAL_SLICE_DIR.mkdir(parents=True, exist_ok=True)


def _load_style_map(docx: ZipFile) -> dict[str, str]:
    styles_root = ET.fromstring(docx.read("word/styles.xml"))
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    style_names: dict[str, str] = {}
    for style in styles_root.findall(".//w:style", namespace):
        style_id = style.get(f"{{{namespace['w']}}}styleId")
        name = style.find("w:name", namespace)
        if style_id:
            style_names[style_id] = (name.get(f"{{{namespace['w']}}}val") if name is not None else style_id).lower()
    return style_names


def load_spec_paragraphs() -> list[DocParagraph]:
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    with ZipFile(SPEC_ARCHIVE_PATH) as outer_zip:
        docx_name = next(name for name in outer_zip.namelist() if name.lower().endswith(".docx"))
        with ZipFile(BytesIO(outer_zip.read(docx_name))) as docx:
            style_names = _load_style_map(docx)
            document_root = ET.fromstring(docx.read("word/document.xml"))

    paragraphs: list[DocParagraph] = []
    for index, paragraph in enumerate(document_root.findall(".//w:p", namespace)):
        text = "".join(node.text or "" for node in paragraph.findall(".//w:t", namespace)).strip()
        if not text:
            continue
        style = paragraph.find("w:pPr/w:pStyle", namespace)
        style_id = style.get(f"{{{namespace['w']}}}val") if style is not None else ""
        paragraphs.append(DocParagraph(index=index, text=text, style=style_names.get(style_id, style_id).lower()))
    return paragraphs


def parse_heading_text(text: str) -> tuple[str, str] | None:
    match = HEADING_TEXT_RE.match(text.strip())
    if not match:
        return None
    return match.group("id"), match.group("title").strip()


def render_markdown(paragraphs: list[DocParagraph]) -> str:
    body_started = False
    lines: list[str] = []
    for paragraph in paragraphs:
        if paragraph.style.startswith("toc"):
            continue
        heading = parse_heading_text(paragraph.text) if paragraph.heading_level is not None else None
        if not body_started:
            body_started = bool(heading and heading[0] == "1")
            if not body_started:
                continue
        if heading and paragraph.heading_level is not None:
            level = max(1, min(6, paragraph.heading_level))
            lines.append(f"{'#' * level} {heading[0]} {heading[1]}")
            continue
        lines.append(paragraph.text)
    return "\n".join(lines)


def extract_target_slices(paragraphs: list[DocParagraph]) -> dict[str, str]:
    slices: dict[str, str] = {}
    for index, paragraph in enumerate(paragraphs):
        heading = parse_heading_text(paragraph.text) if paragraph.heading_level is not None else None
        if not heading or heading[0] not in TARGET_PROCEDURE_IDS:
            continue

        start = index
        start_level = paragraph.heading_level or 6
        end = len(paragraphs)
        for next_index in range(index + 1, len(paragraphs)):
            next_heading = (
                parse_heading_text(paragraphs[next_index].text)
                if paragraphs[next_index].heading_level is not None
                else None
            )
            if next_heading and (paragraphs[next_index].heading_level or 6) <= start_level:
                end = next_index
                break

        lines: list[str] = []
        for current in paragraphs[start:end]:
            current_heading = parse_heading_text(current.text) if current.heading_level is not None else None
            if current_heading and current.heading_level is not None:
                relative_level = 2 + max(0, current.heading_level - start_level)
                lines.append(f"{'#' * min(6, relative_level)} {current_heading[0]} {current_heading[1]}")
                continue
            lines.append(current.text)
        slices[heading[0]] = "\n".join(lines)
    return slices


def extract_nr_rrc_definition_lines(paragraphs: list[DocParagraph]) -> list[str]:
    inside_module = False
    capture_block = False
    lines: list[str] = []

    for paragraph in paragraphs:
        line = paragraph.text
        if line == "-- TAG-NR-RRC-DEFINITIONS-START":
            inside_module = True
            capture_block = True
        if not inside_module:
            continue
        if line == "-- ASN1START":
            capture_block = True
            continue
        if line == "-- ASN1STOP":
            capture_block = False
            continue
        if capture_block:
            lines.append(line)
            if line == "END":
                break
    return lines
