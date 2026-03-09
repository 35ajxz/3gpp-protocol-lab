from __future__ import annotations

from common import GRAPH_OUTPUT_DIR, ensure_dirs, list_efsm_files, read_json, sqlite_connection


SCHEMA_SQL = """
DROP TABLE IF EXISTS procedures;
DROP TABLE IF EXISTS transitions;
DROP TABLE IF EXISTS actions;
DROP TABLE IF EXISTS refs;
DROP TABLE IF EXISTS states;
DROP TABLE IF EXISTS messages;
DROP TABLE IF EXISTS timers;
DROP TABLE IF EXISTS variables;

CREATE TABLE procedures (
  procedure_id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  slug TEXT NOT NULL,
  spec TEXT NOT NULL,
  release TEXT NOT NULL,
  source_document TEXT NOT NULL
);

CREATE TABLE transitions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  procedure_id TEXT NOT NULL,
  step INTEGER NOT NULL,
  source_state TEXT NOT NULL,
  event TEXT NOT NULL,
  guard_expr TEXT,
  target_state TEXT NOT NULL
);

CREATE TABLE actions (
  transition_id INTEGER NOT NULL,
  ordinal INTEGER NOT NULL,
  action_text TEXT NOT NULL
);

CREATE TABLE refs (
  transition_id INTEGER NOT NULL,
  ref_text TEXT NOT NULL
);

CREATE TABLE states (
  procedure_id TEXT NOT NULL,
  state_name TEXT NOT NULL
);

CREATE TABLE messages (
  procedure_id TEXT NOT NULL,
  message_name TEXT NOT NULL
);

CREATE TABLE timers (
  procedure_id TEXT NOT NULL,
  timer_name TEXT NOT NULL
);

CREATE TABLE variables (
  procedure_id TEXT NOT NULL,
  variable_name TEXT NOT NULL
);
"""


def main() -> None:
    ensure_dirs()
    db_path = GRAPH_OUTPUT_DIR / "3gpp_lab.sqlite"
    conn = sqlite_connection(db_path)
    conn.executescript(SCHEMA_SQL)

    for efsm_path in list_efsm_files():
        efsm = read_json(efsm_path)
        procedure = efsm["procedure"]
        procedure_id = procedure["id"]
        conn.execute(
            "INSERT INTO procedures VALUES (?, ?, ?, ?, ?, ?)",
            (
                procedure_id,
                procedure["title"],
                procedure["slug"],
                efsm["spec"],
                efsm["release"],
                efsm["source_document"],
            ),
        )

        state_names = set()
        for transition in efsm["transitions"]:
            cursor = conn.execute(
                "INSERT INTO transitions (procedure_id, step, source_state, event, guard_expr, target_state) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    procedure_id,
                    transition["step"],
                    transition["source_state"],
                    transition["event"],
                    transition.get("guard"),
                    transition["target_state"],
                ),
            )
            transition_id = cursor.lastrowid
            for ordinal, action in enumerate(transition["actions"], start=1):
                conn.execute(
                    "INSERT INTO actions VALUES (?, ?, ?)",
                    (transition_id, ordinal, action),
                )
            for ref in transition["refs"]:
                conn.execute("INSERT INTO refs VALUES (?, ?)", (transition_id, ref))
            state_names.add(transition["source_state"])
            state_names.add(transition["target_state"])

        for state_name in sorted(state_names):
            conn.execute("INSERT INTO states VALUES (?, ?)", (procedure_id, state_name))
        for message_name in efsm["messages"]:
            conn.execute("INSERT INTO messages VALUES (?, ?)", (procedure_id, message_name))
        for timer_name in efsm["timers"]:
            conn.execute("INSERT INTO timers VALUES (?, ?)", (procedure_id, timer_name))
        for variable_name in efsm["variables"]:
            conn.execute("INSERT INTO variables VALUES (?, ?)", (procedure_id, variable_name))

    conn.commit()
    procedures = conn.execute("SELECT COUNT(*) FROM procedures").fetchone()[0]
    transitions = conn.execute("SELECT COUNT(*) FROM transitions").fetchone()[0]
    conn.close()
    print(f"built graph db {db_path} with {procedures} procedures and {transitions} transitions")


if __name__ == "__main__":
    main()
