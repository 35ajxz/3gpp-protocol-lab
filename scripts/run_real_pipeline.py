from __future__ import annotations

from pathlib import Path

from build_runtime_bundle import main as runtime_main
from extract_asn1 import main as extract_asn1_main
from extract_efsm_llm import main as extract_efsm_llm_main
from ingest_real_spec import main as ingest_main
from validate_asn1 import main as validate_asn1_main
from validate_efsm_real import main as validate_efsm_real_main


def count_files(path: Path, suffix: str) -> int:
    return len(list(path.glob(f"*{suffix}")))


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    ingest_main()
    extract_asn1_main()
    validate_asn1_main()
    extract_efsm_llm_main()
    validate_efsm_real_main()
    runtime_main()
    print("---")
    print(f"real_raw: {count_files(root / 'corpus' / 'real' / 'raw', '.md')}")
    print(f"real_slices: {count_files(root / 'corpus' / 'real' / 'slices', '.md')}")
    print(f"efsm_real: {count_files(root / 'outputs' / 'efsm_real', '.json')}")
    print(f"reports_real: {count_files(root / 'outputs' / 'reports_real', '.json')}")
    print(f"asn1_files: {count_files(root / 'outputs' / 'asn1', '.asn1')}")
    print(f"asn1_pdus: {count_files(root / 'outputs' / 'asn1' / 'pdus', '.bin')}")
    print(f"runtime_seed_files: {count_files(root / 'outputs' / 'runtime' / 'seeds', '.json')}")
    print(f"runtime_pdus: {count_files(root / 'outputs' / 'runtime' / 'pdus', '.bin')}")
    print(f"runtime_pcaps: {count_files(root / 'outputs' / 'runtime' / 'pcaps', '.pcap')}")


if __name__ == "__main__":
    main()
