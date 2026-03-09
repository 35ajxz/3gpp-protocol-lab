from __future__ import annotations

import re
from pathlib import Path

from common import CONSTRAINTS_DIR, load_yaml, read_json, write_json


ROOT = Path(__file__).resolve().parents[1]
REAL_EFSM_DIR = ROOT / "outputs" / "efsm_real"
SEED_PREVIEW_DIR = ROOT / "outputs" / "runtime" / "seeds"


def extract_message_name(event: str, actions: list[str]) -> str | None:
    receive_match = re.match(r"receive\(([^)]+)\)", event)
    if receive_match:
        return receive_match.group(1)
    for action in actions:
        send_match = re.match(r"send_message\(([^,)\s]+)", action)
        if send_match:
            return send_match.group(1)
    return None


def nominal_value(field_spec: dict[str, object]):
    if "nominal" in field_spec:
        return field_spec["nominal"]
    if field_spec.get("kind") == "boolean":
        return False
    if field_spec.get("kind") == "enum":
        return field_spec["values"][0]
    if field_spec.get("kind") == "optional_blob":
        return None
    if "min" in field_spec:
        return field_spec["min"]
    return None


def edge_value(field_spec: dict[str, object]):
    if field_spec.get("edge_values"):
        return field_spec["edge_values"][-1]
    if field_spec.get("kind") == "boolean":
        return True
    if field_spec.get("kind") == "optional_blob":
        return "<edge>"
    return nominal_value(field_spec)


def apply_guard_defaults(guard: str | None, payload: dict[str, object]) -> None:
    if not guard:
        return
    parts = [part.strip() for part in guard.split("and")]
    for part in parts:
        negated = part.startswith("not ")
        token = part[4:] if negated else part
        if token.endswith("_present"):
            field_name = token[: -len("_present")]
            payload[field_name] = None if negated else "<present>"


def generate_seeds_for_file(efsm_path, constraints):
    efsm = read_json(efsm_path)
    seeds: list[dict[str, object]] = []
    for transition in efsm["transitions"]:
        message_name = extract_message_name(transition["event"], transition["actions"])
        if not message_name:
            continue
        message_constraints = constraints["messages"].get(message_name, {"fields": {}})
        fields = message_constraints.get("fields", {})

        nominal_payload = {field_name: nominal_value(spec) for field_name, spec in fields.items()}
        apply_guard_defaults(transition.get("guard"), nominal_payload)
        seeds.append(
            {
                "id": f"{efsm['procedure']['id']}-step-{transition['step']}-nominal",
                "procedure_id": efsm["procedure"]["id"],
                "transition_step": transition["step"],
                "message": message_name,
                "mutation_class": "nominal",
                "expected_target_state": transition["target_state"],
                "guard": transition.get("guard"),
                "payload": nominal_payload,
            }
        )

        if fields:
            boundary_payload = {field_name: edge_value(spec) for field_name, spec in fields.items()}
            apply_guard_defaults(transition.get("guard"), boundary_payload)
            seeds.append(
                {
                    "id": f"{efsm['procedure']['id']}-step-{transition['step']}-boundary",
                    "procedure_id": efsm["procedure"]["id"],
                    "transition_step": transition["step"],
                    "message": message_name,
                    "mutation_class": "boundary",
                    "expected_target_state": transition["target_state"],
                    "guard": transition.get("guard"),
                    "payload": boundary_payload,
                }
            )
    return {"procedure": efsm["procedure"], "seeds": seeds}


def main() -> None:
    SEED_PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    constraints = load_yaml(CONSTRAINTS_DIR / "messages.yaml")
    count = 0
    for efsm_path in sorted(REAL_EFSM_DIR.glob("*.json")):
        bundle = generate_seeds_for_file(efsm_path, constraints)
        output_path = SEED_PREVIEW_DIR / f"{bundle['procedure']['slug']}.json"
        write_json(output_path, bundle)
        count += 1
    print(f"generated {count} message seed bundles into {SEED_PREVIEW_DIR}")


if __name__ == "__main__":
    main()
