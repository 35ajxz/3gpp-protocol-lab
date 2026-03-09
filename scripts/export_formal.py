from __future__ import annotations

from common import NUSMV_OUTPUT_DIR, PROMELA_OUTPUT_DIR, ensure_dirs, list_efsm_files, read_json, write_text


def export_promela(efsm: dict[str, object]) -> str:
    procedure = efsm["procedure"]
    state_names = sorted(
        {
            transition["source_state"]
            for transition in efsm["transitions"]
        }
        | {
            transition["target_state"]
            for transition in efsm["transitions"]
        }
    )
    lines = [
        f"/* Auto-generated bootstrap Promela for {procedure['id']} {procedure['title']} */",
        f"mtype = {{ {', '.join(state_names)} }};",
        "",
        "active proctype procedure_model() {",
        f"  mtype state = {efsm['transitions'][0]['source_state']};",
        "  do",
    ]
    for transition in efsm["transitions"]:
        guard = f" && ({transition['guard']})" if transition.get("guard") else ""
        action_comment = "; ".join(transition["actions"])
        lines.append(
            f"  :: (state == {transition['source_state']}{guard}) -> "
            f"/* {transition['event']} | {action_comment} */ state = {transition['target_state']};"
        )
    lines.extend(["  od", "}"])
    return "\n".join(lines)


def export_nusmv(efsm: dict[str, object]) -> str:
    procedure = efsm["procedure"]
    state_names = sorted(
        {
            transition["source_state"]
            for transition in efsm["transitions"]
        }
        | {
            transition["target_state"]
            for transition in efsm["transitions"]
        }
    )
    initial_state = efsm["transitions"][0]["source_state"]
    lines = [
        f"-- Auto-generated bootstrap NuSMV for {procedure['id']} {procedure['title']}",
        "MODULE main",
        f"VAR state : {{{', '.join(state_names)}}};",
        "ASSIGN",
        f"  init(state) := {initial_state};",
        "  next(state) := case",
    ]
    for transition in efsm["transitions"]:
        guard_comment = f" -- guard: {transition['guard']}" if transition.get("guard") else ""
        lines.append(
            f"    state = {transition['source_state']} : {transition['target_state']};{guard_comment}"
        )
    lines.extend(
        [
            "    TRUE : state;",
            "  esac;",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    ensure_dirs()
    count = 0
    for efsm_path in list_efsm_files():
        efsm = read_json(efsm_path)
        slug = efsm["procedure"]["slug"]
        write_text(PROMELA_OUTPUT_DIR / f"{slug}.pml", export_promela(efsm))
        write_text(NUSMV_OUTPUT_DIR / f"{slug}.smv", export_nusmv(efsm))
        count += 1
    print(f"exported formal models for {count} procedures")


if __name__ == "__main__":
    main()
