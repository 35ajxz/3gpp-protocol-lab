from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONSTRAINTS_DIR = ROOT / "constraints"
PROCEDURE_RE = re.compile(r"^##\s+(?P<id>\d+(?:\.\d+)+)\s+(?P<title>.+)$")


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


def flatten_text(values) -> str:
    return " ".join(values).lower()
