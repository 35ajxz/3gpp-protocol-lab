from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile

from common import PROCEDURE_RE, slugify_procedure, write_json


ROOT = Path(__file__).resolve().parents[1]
REAL_SLICE_DIR = ROOT / "corpus" / "real" / "slices"
REAL_EFSM_DIR = ROOT / "outputs" / "efsm_real"
SCHEMA_PATH = ROOT / "schemas" / "efsm.codex.schema.json"
KEEP_KEYWORDS = (
    "purpose of this procedure",
    "the ue initiates",
    "the ue shall",
    "start timer",
    "stop timer",
    "submit the",
    "initiate transmission",
    "send",
    "receive",
    "enter rrc_",
    "enter rrc",
    "rrcsetuprequest",
    "rrcsetup",
    "rrcresumerequest",
    "rrcresumerequest1",
    "rrcresume",
    "rrcresumecomplete",
    "rrcreject",
    "rrcrelease",
    "resumecause",
    "establishmentcause",
    "pendingrna-update",
    "pendingrna update",
    "fullconfig",
    "t300",
    "t302",
    "t319",
    "t319a",
    "t331",
    "t380",
    "t390",
)

PROMPT_TEMPLATE = """你是一个 3GPP RRC EFSM 提取器。

任务：从下面这段真实规范切片中提取一个紧凑但忠实的 EFSM。

硬性要求：
- 返回内容只能是 JSON，且必须满足给定 schema。
- 保持 `spec`=`TS 38.331`，`release`=`Rel-17`。
- `source_document` 必须等于 `{source_document}`。
- `procedure.id` 必须等于 `{procedure_id}`。
- `procedure.title` 必须等于 `{procedure_title}`。
- `procedure.slug` 必须等于 `{procedure_slug}`。
- `messages` / `timers` / `variables` 只放本段里确实出现或直接可推断的标识符。
- `transitions` 请给出 3 到 12 个最关键的步骤，按 `step` 升序。
- `guard` 没有明确条件时写 `null`。
- 若有发消息动作，请用 `send_message(MessageName,field1,field2)` 形式。
- 若有收消息事件，请用 `receive(MessageName)` 形式。
- `refs` 只写本段中出现的 clause 引用，例如 `5.3.13.3`。

状态命名规则：
- 采用简洁的大写状态名，如 `RRC_IDLE`、`RRC_SETUP_REQUESTED`、`RRC_INACTIVE`、`RRC_CONNECTED`、`PROCEDURE_ABORTED`。

输入切片：
```text
{slice_text}
```"""


def ordered_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def parse_header(slice_path: Path) -> tuple[str, str, str]:
    for line in slice_path.read_text().splitlines():
        match = PROCEDURE_RE.match(line)
        if match:
            procedure_id = match.group("id")
            title = match.group("title")
            return procedure_id, title, slugify_procedure(procedure_id, title)
    raise ValueError(f"missing procedure header in {slice_path}")


def compress_slice_text(slice_text: str) -> str:
    selected: list[str] = []
    for line in slice_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        lowered = stripped.lower()
        if stripped.startswith("#"):
            selected.append(stripped)
            continue
        if stripped.startswith(("1>", "2>", "3>", "4>")) and any(keyword in lowered for keyword in KEEP_KEYWORDS):
            selected.append(stripped)
            continue
        if any(keyword in lowered for keyword in KEEP_KEYWORDS):
            selected.append(stripped)

    if len(selected) < 40:
        return slice_text
    return "\n".join(selected[:220])


def run_codex(slice_path: Path) -> dict[str, object]:
    procedure_id, procedure_title, procedure_slug = parse_header(slice_path)
    prompt = PROMPT_TEMPLATE.format(
        source_document=slice_path.name,
        procedure_id=procedure_id,
        procedure_title=procedure_title,
        procedure_slug=procedure_slug,
        slice_text=compress_slice_text(slice_path.read_text()),
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        output_path = Path(temp_dir) / "codex-output.json"
        cmd = [
            "codex",
            "exec",
            "--skip-git-repo-check",
            "--cd",
            str(ROOT),
            "--sandbox",
            "danger-full-access",
            "-c",
            'model_reasoning_effort="low"',
            "--output-schema",
            str(SCHEMA_PATH),
            "-o",
            str(output_path),
            prompt,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or f"codex failed for {slice_path.name}")
        data = json.loads(output_path.read_text())

    transitions = []
    for index, transition in enumerate(data.get("transitions", []), start=1):
        transitions.append(
            {
                "step": index,
                "source_state": str(transition["source_state"]),
                "event": str(transition["event"]),
                "guard": transition.get("guard"),
                "actions": [str(action) for action in transition["actions"]],
                "target_state": str(transition["target_state"]),
                "refs": [str(ref) for ref in transition["refs"]],
            }
        )

    return {
        "spec": "TS 38.331",
        "release": "Rel-17",
        "source_document": slice_path.name,
        "procedure": {
            "id": procedure_id,
            "title": procedure_title,
            "slug": procedure_slug,
        },
        "messages": ordered_unique([str(item) for item in data.get("messages", [])]),
        "timers": ordered_unique([str(item) for item in data.get("timers", [])]),
        "variables": ordered_unique([str(item) for item in data.get("variables", [])]),
        "transitions": transitions,
    }


def main() -> None:
    REAL_EFSM_DIR.mkdir(parents=True, exist_ok=True)
    count = 0
    for slice_path in sorted(REAL_SLICE_DIR.glob("*.md"), key=lambda path: (path.stat().st_size, path.name)):
        efsm = run_codex(slice_path)
        write_json(REAL_EFSM_DIR / f"{efsm['procedure']['slug']}.json", efsm)
        count += 1
    print(f"extracted {count} real EFSM files into {REAL_EFSM_DIR}")


if __name__ == "__main__":
    main()
