from __future__ import annotations

from pathlib import Path
import re

from common import write_json, write_text
from docx_3gpp import extract_nr_rrc_definition_lines, load_spec_paragraphs


ROOT = Path(__file__).resolve().parents[1]
ASN1_OUTPUT_DIR = ROOT / "outputs" / "asn1"
ASN1_OUTPUT_PATH = ASN1_OUTPUT_DIR / "NR-RRC-Definitions.asn1"

KEYWORDS = [
    "ENUMERATED",
    "SEQUENCE",
    "CHOICE",
    "INTEGER",
    "BOOLEAN",
    "NULL",
    "OCTET STRING",
    "BIT STRING",
    "PrintableString",
    "UTF8String",
    "VisibleString",
    "IA5String",
]
KEYWORD_RE = "|".join(re.escape(keyword) for keyword in KEYWORDS)


def normalize_asn1_line(line: str) -> str:
    if not re.match(r"^SetupRelease\b.*::=", line):
        line = re.sub(r"SetupRelease\s*\{\s*([^}]+?)\s*\}", r"CHOICE { release NULL, setup \1 }", line)
    line = re.sub(r"([A-Za-z0-9\)\]])(?=(" + KEYWORD_RE + r"))", r"\1 ", line)
    line = re.sub(r"\b(ENUMERATED|SEQUENCE|SET|CHOICE)\{", r"\1 {", line)
    line = re.sub(r"\b(INTEGER|BOOLEAN|NULL)\{", r"\1 {", line)
    line = re.sub(r"\b(BIT STRING|OCTET STRING)\{", r"\1 {", line)
    line = re.sub(r"::=\{", "::= {", line)
    return line


def main() -> None:
    ASN1_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    paragraphs = load_spec_paragraphs()
    raw_lines = extract_nr_rrc_definition_lines(paragraphs)
    normalized_lines = [normalize_asn1_line(line) for line in raw_lines]
    write_text(ASN1_OUTPUT_PATH, "\n".join(normalized_lines))
    write_json(
        ASN1_OUTPUT_DIR / "NR-RRC-Definitions.meta.json",
        {
            "line_count": len(normalized_lines),
            "contains_module_header": any("NR-RRC-Definitions DEFINITIONS AUTOMATIC TAGS ::=" in line for line in normalized_lines),
            "contains_module_end": normalized_lines[-1] == "END",
            "pass": bool(normalized_lines),
        },
    )
    print(f"extracted real ASN.1 module to {ASN1_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
