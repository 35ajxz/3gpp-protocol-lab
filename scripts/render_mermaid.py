from __future__ import annotations

from common import MERMAID_OUTPUT_DIR, ensure_dirs, list_efsm_files, read_json, write_text


def render_file(efsm_path):
    efsm = read_json(efsm_path)
    lines = ["stateDiagram-v2"]
    for transition in efsm["transitions"]:
        guard = f" [{transition['guard']}]" if transition.get("guard") else ""
        action_text = ", ".join(transition["actions"])
        label = f"{transition['event']}{guard} / {action_text}"
        lines.append(f"    {transition['source_state']} --> {transition['target_state']}: {label}")
    output_path = MERMAID_OUTPUT_DIR / (efsm["procedure"]["slug"] + ".mmd")
    write_text(output_path, "\n".join(lines))


def main() -> None:
    ensure_dirs()
    for efsm_path in list_efsm_files():
        render_file(efsm_path)
    print(f"rendered {len(list_efsm_files())} Mermaid diagrams into {MERMAID_OUTPUT_DIR}")


if __name__ == "__main__":
    main()
