from __future__ import annotations

from collections import Counter
from copy import deepcopy
from pathlib import Path
import re
from typing import Any

from common import load_yaml, read_json, write_json


ROOT = Path(__file__).resolve().parents[1]
LOGIC_RULES_PATH = ROOT / "constraints" / "logic_rules.yaml"
REAL_EFSM_DIR = ROOT / "outputs" / "efsm_real"
LOGIC_OUTPUT_DIR = ROOT / "outputs" / "logic"
LOGIC_TRACE_DIR = LOGIC_OUTPUT_DIR / "traces"

START_TIMER_PARENS_RE = re.compile(r"start_timer\((T[0-9A-Za-z]+)\)")
STOP_TIMER_PARENS_RE = re.compile(r"stop_timer\((T[0-9A-Za-z]+)\)")
START_TIMER_TEXT_RE = re.compile(r"\bstart (T[0-9A-Za-z]+)\b")
STOP_TIMER_TEXT_RE = re.compile(r"\bstop (?:timer )?(T[0-9A-Za-z]+)\b")
SET_VAR_RE = re.compile(r"\bset ([A-Za-z0-9_-]+) to ([A-Za-z0-9_<>\-]+)")


def ensure_logic_dirs() -> None:
    for path in (LOGIC_OUTPUT_DIR, LOGIC_TRACE_DIR):
        path.mkdir(parents=True, exist_ok=True)


def normalize_guard(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    if not text or text.lower() == "null":
        return None
    return text


def load_real_models() -> dict[str, dict[str, Any]]:
    models: dict[str, dict[str, Any]] = {}
    for path in sorted(REAL_EFSM_DIR.glob("*.json")):
        payload = read_json(path)
        models[payload["procedure"]["id"]] = payload
    return models


def load_logic_rules() -> dict[str, Any]:
    return load_yaml(LOGIC_RULES_PATH)


def safe_name(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "-", value).strip("-")


def apply_actions(
    actions: list[str],
    current_state: str,
    timers: set[str],
    context: dict[str, Any],
) -> tuple[str, set[str], dict[str, Any]]:
    next_state = current_state
    next_timers = set(timers)
    next_context = dict(context)
    for action in actions:
        for regex in (START_TIMER_PARENS_RE, START_TIMER_TEXT_RE):
            match = regex.search(action)
            if match:
                next_timers.add(match.group(1))
        for regex in (STOP_TIMER_PARENS_RE, STOP_TIMER_TEXT_RE):
            match = regex.search(action)
            if match:
                next_timers.discard(match.group(1))
        if action.startswith("enter "):
            next_state = action.split("enter ", 1)[1].strip()
        set_match = SET_VAR_RE.search(action)
        if set_match:
            next_context[set_match.group(1)] = set_match.group(2)
    return next_state, next_timers, next_context


class ExecutableProcedureModel:
    def __init__(self, efsm: dict[str, Any], initial_state: str) -> None:
        self.efsm = efsm
        self.initial_state = initial_state
        self.transitions = sorted(efsm["transitions"], key=lambda item: item["step"])

    def match_transition(self, state: str, event: str, guard_contains: str | None = None) -> dict[str, Any] | None:
        matches = [
            transition
            for transition in self.transitions
            if transition["source_state"] == state and transition["event"] == event
        ]
        if guard_contains:
            matches = [
                transition
                for transition in matches
                if guard_contains in (normalize_guard(transition.get("guard")) or "")
            ]
        if not matches:
            return None
        return matches[0]


class ReferenceTarget:
    name = "reference_model"

    def apply_step(
        self,
        model: ExecutableProcedureModel,
        state: str,
        timers: set[str],
        context: dict[str, Any],
        step: dict[str, Any],
    ) -> dict[str, Any]:
        transition = model.match_transition(state, step["event"], step.get("guard_contains"))
        if transition is None:
            return {
                "accepted": False,
                "state_after": state,
                "timers_after": sorted(timers),
                "context_after": context,
                "matched_transition_step": None,
                "matched_guard": None,
                "notes": "no matching transition",
            }

        transition_guard = normalize_guard(transition.get("guard"))
        next_state, next_timers, next_context = apply_actions(transition["actions"], state, timers, context)
        if transition["target_state"]:
            next_state = transition["target_state"]
        return {
            "accepted": True,
            "state_after": next_state,
            "timers_after": sorted(next_timers),
            "context_after": next_context,
            "matched_transition_step": transition["step"],
            "matched_guard": transition_guard,
            "refs": transition.get("refs", []),
            "notes": "reference transition matched",
        }


class PermissiveTarget:
    name = "permissive_logic_target"

    def apply_step(
        self,
        model: ExecutableProcedureModel,
        state: str,
        timers: set[str],
        context: dict[str, Any],
        step: dict[str, Any],
    ) -> dict[str, Any]:
        strict = ReferenceTarget().apply_step(model, state, timers, context, step)
        if strict["accepted"]:
            return strict

        procedure_id = model.efsm["procedure"]["id"]
        event = step["event"]
        next_timers = set(timers)
        next_context = dict(context)

        if procedure_id == "5.3.3":
            if event == "T300_expiry" and state == "RRC_SETUP_REQUESTED":
                return {
                    "accepted": True,
                    "state_after": "RRC_SETUP_REQUESTED",
                    "timers_after": sorted(next_timers),
                    "context_after": next_context,
                    "matched_transition_step": "synthetic-timeout-ignore",
                    "matched_guard": None,
                    "notes": "accepted timeout but ignored abort",
                }
            if event in {"receive(RRCSetup)", "receive(RRCResume)"} and state in {
                "RRC_IDLE",
                "RRC_SETUP_REQUESTED",
                "PROCEDURE_ABORTED",
                "RRC_CONNECTED",
            }:
                next_timers.discard("T300")
                next_timers.discard("T301")
                next_timers.discard("T319")
                next_timers.discard("T319a")
                next_timers.discard("T320")
                next_timers.discard("T331")
                next_timers.discard("T380")
                next_timers.discard("T390")
                next_timers.discard("T302")
                return {
                    "accepted": True,
                    "state_after": "RRC_CONNECTED",
                    "timers_after": sorted(next_timers),
                    "context_after": next_context,
                    "matched_transition_step": "synthetic-cross-accept",
                    "matched_guard": step.get("guard_contains"),
                    "notes": "accepted setup/resume control-plane response in permissive mode",
                }

        if procedure_id == "5.3.13":
            if event == "T319_expiry_or_integrity_failure_or_SDT_failure" and state == "RRC_INACTIVE":
                return {
                    "accepted": True,
                    "state_after": "RRC_INACTIVE",
                    "timers_after": sorted(next_timers),
                    "context_after": next_context,
                    "matched_transition_step": "synthetic-timeout-ignore",
                    "matched_guard": None,
                    "notes": "accepted resume failure event but ignored abort",
                }
            if event in {"receive(RRCResume)", "receive(RRCSetup)"} and state in {
                "RRC_INACTIVE",
                "PROCEDURE_ABORTED",
                "RRC_CONNECTED",
            }:
                next_timers.discard("T319")
                next_timers.discard("T319a")
                next_timers.discard("T380")
                next_timers.discard("T331")
                next_timers.discard("T320")
                next_timers.discard("T390")
                next_timers.discard("T302")
                return {
                    "accepted": True,
                    "state_after": "RRC_CONNECTED",
                    "timers_after": sorted(next_timers),
                    "context_after": next_context,
                    "matched_transition_step": "synthetic-cross-accept",
                    "matched_guard": None,
                    "notes": "accepted resume/setup response in permissive mode",
                }

        return strict


def execute_case(
    target: ReferenceTarget | PermissiveTarget,
    model: ExecutableProcedureModel,
    case: dict[str, Any],
) -> dict[str, Any]:
    state = model.initial_state
    timers: set[str] = set()
    context: dict[str, Any] = {}
    trace_steps: list[dict[str, Any]] = []

    for index, step in enumerate(case["steps"], start=1):
        result = target.apply_step(model, state, timers, context, step)
        trace_steps.append(
            {
                "index": index,
                "event": step["event"],
                "guard_contains": step.get("guard_contains"),
                "state_before": state,
                "timers_before": sorted(timers),
                "accepted": result["accepted"],
                "state_after": result["state_after"],
                "timers_after": result["timers_after"],
                "matched_transition_step": result["matched_transition_step"],
                "matched_guard": result.get("matched_guard"),
                "notes": result["notes"],
            }
        )
        state = result["state_after"]
        timers = set(result["timers_after"])
        context = result["context_after"]

    return {
        "target": target.name,
        "procedure_id": case["procedure_id"],
        "scenario_id": case["scenario_id"],
        "case_id": case["case_id"],
        "perturbation": case["perturbation"],
        "initial_state": model.initial_state,
        "final_state": state,
        "accepted_steps": sum(1 for item in trace_steps if item["accepted"]),
        "steps": trace_steps,
    }


def generate_cases(rules: dict[str, Any]) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for procedure_id, procedure_rules in rules["procedures"].items():
        for scenario in procedure_rules["scenarios"]:
            base_steps = deepcopy(scenario["steps"])
            cases.append(
                {
                    "case_id": f"{procedure_id}-{scenario['id']}-nominal",
                    "procedure_id": procedure_id,
                    "scenario_id": scenario["id"],
                    "description": scenario["description"],
                    "perturbation": "nominal",
                    "steps": deepcopy(base_steps),
                }
            )
            for perturbation in procedure_rules.get("perturbations", []):
                mutated = deepcopy(base_steps)
                perturbation_type = perturbation["type"]
                label = perturbation.get("label", perturbation_type)
                if perturbation_type == "duplicate_last_step":
                    mutated.insert(len(mutated), deepcopy(mutated[-1]))
                elif perturbation_type == "move_last_to_front":
                    mutated = [deepcopy(mutated[-1]), *deepcopy(mutated[:-1])]
                elif perturbation_type == "drop_last_step":
                    mutated = deepcopy(mutated[:-1])
                elif perturbation_type == "append_last_step":
                    mutated.append(deepcopy(mutated[-1]))
                elif perturbation_type == "insert_timeout_before_last":
                    mutated.insert(len(mutated) - 1, {"event": perturbation["event"]})
                elif perturbation_type == "replace_last_step":
                    replacement = {"event": perturbation["event"]}
                    if "guard_contains" in perturbation:
                        replacement["guard_contains"] = perturbation["guard_contains"]
                    mutated[-1] = replacement
                else:
                    raise ValueError(f"Unknown perturbation type: {perturbation_type}")

                cases.append(
                    {
                        "case_id": safe_name(f"{procedure_id}-{scenario['id']}-{label}"),
                        "procedure_id": procedure_id,
                        "scenario_id": scenario["id"],
                        "description": scenario["description"],
                        "perturbation": label,
                        "steps": mutated,
                    }
                )
    return cases


def evaluate_invariants(result: dict[str, Any], procedure_rules: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    steps = result["steps"]
    accepted_events = [item["event"] for item in steps if item["accepted"]]
    final_state = result["final_state"]

    for invariant in procedure_rules.get("invariants", []):
        invariant_type = invariant["type"]
        if invariant_type == "require_history_event":
            if final_state == invariant["trigger_state"] and invariant["expected_event"] not in accepted_events:
                findings.append(
                    {
                        "type": "invariant_violation",
                        "invariant_id": invariant["id"],
                        "summary": f"final state {final_state} was reached without required event {invariant['expected_event']}",
                    }
                )
        elif invariant_type == "forbid_event":
            for item in steps:
                if item["accepted"] and item["event"] == invariant["event"]:
                    findings.append(
                        {
                            "type": "invariant_violation",
                            "invariant_id": invariant["id"],
                            "summary": f"forbidden event {item['event']} was accepted in state {item['state_before']}",
                            "step_index": item["index"],
                        }
                    )
        elif invariant_type == "require_state_after_event":
            for item in steps:
                if item["accepted"] and item["event"] == invariant["event"] and item["state_after"] != invariant["expected_state"]:
                    findings.append(
                        {
                            "type": "invariant_violation",
                            "invariant_id": invariant["id"],
                            "summary": f"event {item['event']} ended in {item['state_after']} instead of {invariant['expected_state']}",
                            "step_index": item["index"],
                        }
                    )
        elif invariant_type == "forbid_state_after_event":
            for item in steps:
                if item["accepted"] and item["event"] == invariant["event"] and item["state_after"] == invariant["forbidden_state"]:
                    findings.append(
                        {
                            "type": "invariant_violation",
                            "invariant_id": invariant["id"],
                            "summary": f"event {item['event']} incorrectly produced forbidden state {item['state_after']}",
                            "step_index": item["index"],
                        }
                    )
        elif invariant_type == "require_timer_cleared":
            for item in steps:
                guard_contains = invariant.get("guard_contains")
                guard_match = guard_contains is None or guard_contains in (item.get("matched_guard") or "")
                if item["accepted"] and item["event"] == invariant["event"] and guard_match:
                    if invariant["timer"] in item["timers_after"]:
                        findings.append(
                            {
                                "type": "invariant_violation",
                                "invariant_id": invariant["id"],
                                "summary": f"timer {invariant['timer']} remained active after {item['event']}",
                                "step_index": item["index"],
                            }
                        )
        elif invariant_type == "require_guard_for_final_state":
            if final_state == invariant["trigger_state"]:
                matched = any(
                    item["accepted"]
                    and item["event"] == invariant["event"]
                    and invariant["guard_contains"] in (item.get("matched_guard") or "")
                    for item in steps
                )
                if not matched:
                    findings.append(
                        {
                            "type": "invariant_violation",
                            "invariant_id": invariant["id"],
                            "summary": f"final state {final_state} was reached without guard containing {invariant['guard_contains']}",
                        }
                    )
        else:
            raise ValueError(f"Unknown invariant type: {invariant_type}")
    return findings


def compare_results(reference: dict[str, Any], candidate: dict[str, Any], procedure_rules: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for ref_step, cand_step in zip(reference["steps"], candidate["steps"]):
        if cand_step["accepted"] and not ref_step["accepted"]:
            findings.append(
                {
                    "type": "negative_acceptance",
                    "summary": f"candidate accepted {cand_step['event']} from {cand_step['state_before']} while reference rejected it",
                    "step_index": cand_step["index"],
                }
            )
        if ref_step["accepted"] and not cand_step["accepted"]:
            findings.append(
                {
                    "type": "unexpected_rejection",
                    "summary": f"candidate rejected {cand_step['event']} from {cand_step['state_before']} while reference accepted it",
                    "step_index": cand_step["index"],
                }
            )
        if cand_step["state_after"] != ref_step["state_after"]:
            findings.append(
                {
                    "type": "state_divergence",
                    "summary": f"candidate reached {cand_step['state_after']} while reference reached {ref_step['state_after']} after {cand_step['event']}",
                    "step_index": cand_step["index"],
                }
            )

    findings.extend(evaluate_invariants(candidate, procedure_rules))
    return findings


def run_campaign() -> dict[str, Any]:
    ensure_logic_dirs()
    rules = load_logic_rules()
    models = load_real_models()
    reference_target = ReferenceTarget()
    candidate_target = PermissiveTarget()
    cases = generate_cases(rules)

    all_findings: list[dict[str, Any]] = []
    case_reports: list[dict[str, Any]] = []

    for case in cases:
        model = ExecutableProcedureModel(models[case["procedure_id"]], rules["procedures"][case["procedure_id"]]["initial_state"])
        reference_result = execute_case(reference_target, model, case)
        candidate_result = execute_case(candidate_target, model, case)
        findings = compare_results(reference_result, candidate_result, rules["procedures"][case["procedure_id"]])
        case_report = {
            "case_id": case["case_id"],
            "procedure_id": case["procedure_id"],
            "scenario_id": case["scenario_id"],
            "perturbation": case["perturbation"],
            "steps": case["steps"],
            "reference": reference_result,
            "candidate": candidate_result,
            "findings": findings,
        }
        case_reports.append(case_report)
        write_json(LOGIC_TRACE_DIR / f"{case['case_id']}.json", case_report)
        for finding in findings:
            finding_record = dict(finding)
            finding_record["case_id"] = case["case_id"]
            finding_record["procedure_id"] = case["procedure_id"]
            finding_record["scenario_id"] = case["scenario_id"]
            finding_record["perturbation"] = case["perturbation"]
            all_findings.append(finding_record)

    summary = {
        "reference_target": reference_target.name,
        "candidate_target": candidate_target.name,
        "case_count": len(cases),
        "finding_count": len(all_findings),
        "cases_with_findings": sum(1 for report in case_reports if report["findings"]),
        "finding_types": dict(Counter(finding["type"] for finding in all_findings)),
        "procedures": dict(Counter(case["procedure_id"] for case in cases)),
        "pass": len(all_findings) == 0,
    }

    write_json(LOGIC_OUTPUT_DIR / "cases.json", cases)
    write_json(LOGIC_OUTPUT_DIR / "findings.json", all_findings)
    write_json(LOGIC_OUTPUT_DIR / "summary.json", summary)
    return summary
