from __future__ import annotations

from collections import defaultdict, deque

from common import CONSTRAINTS_DIR, PROPERTY_OUTPUT_DIR, ensure_dirs, list_efsm_files, load_yaml, read_json, write_json


def build_graph(transitions):
    graph = defaultdict(list)
    for transition in transitions:
        graph[transition["source_state"]].append(transition)
    return graph


def reachable_states(start_state, graph):
    seen = {start_state}
    queue = deque([start_state])
    while queue:
        state = queue.popleft()
        for transition in graph.get(state, []):
            target = transition["target_state"]
            if target not in seen:
                seen.add(target)
                queue.append(target)
    return seen


def evaluate_procedure(efsm, policy):
    graph = build_graph(efsm["transitions"])
    start_state = policy["start_state"]
    allowed_terminal = set(policy.get("allowed_terminal_states", []))
    reachable = reachable_states(start_state, graph)
    states = {
        transition["source_state"]
        for transition in efsm["transitions"]
    } | {
        transition["target_state"]
        for transition in efsm["transitions"]
    }

    dead_ends = sorted(
        state
        for state in states
        if state not in graph and state not in allowed_terminal
    )

    assertions = []
    for item in policy.get("assertions", []):
        if item["kind"] == "reachability":
            passed = item["target_state"] in reachable
            assertions.append({"assertion": item, "pass": passed})
        elif item["kind"] == "event_target":
            passed = any(
                transition["event"] == item["event"] and transition["target_state"] == item["target_state"]
                for transition in efsm["transitions"]
            )
            assertions.append({"assertion": item, "pass": passed})

    return {
        "procedure_id": efsm["procedure"]["id"],
        "reachable_states": sorted(reachable),
        "dead_ends": dead_ends,
        "assertions": assertions,
        "pass": (not dead_ends) and all(item["pass"] for item in assertions),
    }


def main() -> None:
    ensure_dirs()
    policies = load_yaml(CONSTRAINTS_DIR / "properties.yaml")["procedures"]
    for efsm_path in list_efsm_files():
        efsm = read_json(efsm_path)
        procedure_id = efsm["procedure"]["id"]
        report = evaluate_procedure(efsm, policies[procedure_id])
        write_json(PROPERTY_OUTPUT_DIR / efsm_path.name, report)
    print(f"checked properties for {len(list_efsm_files())} procedures")


if __name__ == "__main__":
    main()
