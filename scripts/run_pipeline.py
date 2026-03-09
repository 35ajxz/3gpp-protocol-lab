from __future__ import annotations

from pathlib import Path

from slice_procedures import main as slice_main
from build_graph import main as graph_main
from check_properties import main as property_main
from export_formal import main as formal_main
from extract_efsm import main as extract_main
from generate_paths import main as path_main
from generate_seeds import main as seed_main
from retrieve import rank_query
from render_mermaid import main as mermaid_main
from validate_efsm import main as validate_main
from common import RETRIEVAL_OUTPUT_DIR, write_json


def count_files(path: Path, suffix: str) -> int:
    return len(list(path.glob(f"*{suffix}")))


def main() -> None:
    slice_main()
    extract_main()
    validate_main()
    write_json(RETRIEVAL_OUTPUT_DIR / "last_query.json", rank_query("RRC resume fullConfig"))
    graph_main()
    formal_main()
    property_main()
    path_main()
    mermaid_main()
    seed_main()
    root = Path(__file__).resolve().parents[1]
    print("---")
    print(f"slices: {count_files(root / 'corpus' / 'slices', '.md')}")
    print(f"efsm: {count_files(root / 'outputs' / 'efsm', '.json')}")
    print(f"reports: {count_files(root / 'outputs' / 'reports', '.json')}")
    print(f"retrieval: {count_files(root / 'outputs' / 'retrieval', '.json')}")
    print(f"formal_promela: {count_files(root / 'outputs' / 'formal' / 'promela', '.pml')}")
    print(f"formal_nusmv: {count_files(root / 'outputs' / 'formal' / 'nusmv', '.smv')}")
    print(f"properties: {count_files(root / 'outputs' / 'properties', '.json')}")
    print(f"paths: {count_files(root / 'outputs' / 'paths', '.json')}")
    print(f"mermaid: {count_files(root / 'outputs' / 'mermaid', '.mmd')}")
    print(f"seeds: {count_files(root / 'outputs' / 'seeds', '.json')}")


if __name__ == "__main__":
    main()
