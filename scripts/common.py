from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Iterable

import yaml

ROOT = Path(__file__).resolve().parents[1]
CORPUS_RAW_DIR = ROOT / "corpus" / "raw"
CORPUS_SLICE_DIR = ROOT / "corpus" / "slices"
CONSTRAINTS_DIR = ROOT / "constraints"
OUTPUTS_DIR = ROOT / "outputs"
EFSM_OUTPUT_DIR = OUTPUTS_DIR / "efsm"
REPORT_OUTPUT_DIR = OUTPUTS_DIR / "reports"
RETRIEVAL_OUTPUT_DIR = OUTPUTS_DIR / "retrieval"
GRAPH_OUTPUT_DIR = OUTPUTS_DIR / "graph"
FORMAL_OUTPUT_DIR = OUTPUTS_DIR / "formal"
PROMELA_OUTPUT_DIR = FORMAL_OUTPUT_DIR / "promela"
NUSMV_OUTPUT_DIR = FORMAL_OUTPUT_DIR / "nusmv"
PROPERTY_OUTPUT_DIR = OUTPUTS_DIR / "properties"
PATH_OUTPUT_DIR = OUTPUTS_DIR / "paths"
MERMAID_OUTPUT_DIR = OUTPUTS_DIR / "mermaid"
SEED_OUTPUT_DIR = OUTPUTS_DIR / "seeds"

PROCEDURE_RE = re.compile(r"^##\s+(?P<id>\d+(?:\.\d+)+)\s+(?P<title>.+)$")
TRANSITION_RE = re.compile(
    r"^\s*(?P<step>\d+)>\s+src=(?P<src>\S+)\s+event=(?P<event>\S+)"
    r"(?:\s+guard=(?P<guard>.+?))?\s+actions=(?P<actions>.+?)\s+dst=(?P<dst>\S+)\s+refs=(?P<refs>.+)$"
)


def ensure_dirs() -> None:
    for path in (
        CORPUS_SLICE_DIR,
        EFSM_OUTPUT_DIR,
        REPORT_OUTPUT_DIR,
        RETRIEVAL_OUTPUT_DIR,
        GRAPH_OUTPUT_DIR,
        PROMELA_OUTPUT_DIR,
        NUSMV_OUTPUT_DIR,
        PROPERTY_OUTPUT_DIR,
        PATH_OUTPUT_DIR,
        MERMAID_OUTPUT_DIR,
        SEED_OUTPUT_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)


def slugify_procedure(procedure_id: str, title: str) -> str:
    slug_title = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return f"{procedure_id}-{slug_title}"


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=False) + "\n")


def read_json(path: Path) -> object:
    return json.loads(path.read_text())


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n")


def load_yaml(path: Path) -> object:
    return yaml.safe_load(path.read_text())


def list_slice_files() -> list[Path]:
    return sorted(CORPUS_SLICE_DIR.glob("*.md"))


def list_efsm_files() -> list[Path]:
    return sorted(EFSM_OUTPUT_DIR.glob("*.json"))


def split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_transition_line(line: str) -> dict[str, object]:
    match = TRANSITION_RE.match(line.strip())
    if not match:
        raise ValueError(f"Invalid transition line: {line}")
    actions = [item.strip() for item in match.group("actions").split(";") if item.strip()]
    refs = split_csv(match.group("refs"))
    return {
        "step": int(match.group("step")),
        "source_state": match.group("src"),
        "event": match.group("event"),
        "guard": match.group("guard"),
        "actions": actions,
        "target_state": match.group("dst"),
        "refs": refs,
    }


def flatten_text(values: Iterable[str]) -> str:
    return " ".join(values).lower()


def procedure_index_from_slices() -> dict[str, str]:
    index: dict[str, str] = {}
    for path in list_slice_files():
        lines = path.read_text().splitlines()
        for line in lines:
            match = PROCEDURE_RE.match(line)
            if match:
                index[match.group("id")] = match.group("title")
                break
    return index


def sqlite_connection(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(path)
