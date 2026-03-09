from __future__ import annotations

from collections import defaultdict

from common import PATH_OUTPUT_DIR, ensure_dirs, list_efsm_files, read_json, write_json


def generate_path_bundle(efsm):
    outgoing = defaultdict(list)
    for transition in efsm["transitions"]:
        outgoing[transition["source_state"]].append(transition)

    one_switch = []
    two_switch = []
    for transition in efsm["transitions"]:
        one_switch.append(
            {
                "id": f"{efsm['procedure']['id']}-transition-{transition['step']}",
                "steps": [transition["step"]],
                "states": [transition["source_state"], transition["target_state"]],
            }
        )
        for next_transition in outgoing.get(transition["target_state"], []):
            two_switch.append(
                {
                    "id": f"{efsm['procedure']['id']}-path-{transition['step']}-{next_transition['step']}",
                    "steps": [transition["step"], next_transition["step"]],
                    "states": [
                        transition["source_state"],
                        transition["target_state"],
                        next_transition["target_state"],
                    ],
                }
            )

    return {
        "procedure": efsm["procedure"],
        "transition_coverage": one_switch,
        "two_switch_paths": two_switch,
    }


def main() -> None:
    ensure_dirs()
    for efsm_path in list_efsm_files():
        efsm = read_json(efsm_path)
        bundle = generate_path_bundle(efsm)
        write_json(PATH_OUTPUT_DIR / efsm_path.name, bundle)
    print(f"generated path plans for {len(list_efsm_files())} procedures")


if __name__ == "__main__":
    main()
