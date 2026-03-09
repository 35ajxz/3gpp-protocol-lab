from __future__ import annotations

from pathlib import Path
import subprocess

from scapy.all import Ether, IP, Raw, UDP, wrpcap

from common import CONSTRAINTS_DIR, load_yaml, read_json, write_json, write_text
from generate_seeds import generate_seeds_for_file
from validate_asn1 import build_resume_request, build_setup_request, compile_nr_rrc


ROOT = Path(__file__).resolve().parents[1]
REAL_EFSM_DIR = ROOT / "outputs" / "efsm_real"
RUNTIME_DIR = ROOT / "outputs" / "runtime"
RUNTIME_SEED_DIR = RUNTIME_DIR / "seeds"
RUNTIME_PDU_DIR = RUNTIME_DIR / "pdus"
RUNTIME_PCAP_DIR = RUNTIME_DIR / "pcaps"
RUNTIME_OAI_DIR = RUNTIME_DIR / "oai"
BASE_COMPOSE_PATH = ROOT / "targets" / "oai" / "docker-compose.yaml"
UDP_INJECTOR_PATH = ROOT / "scripts" / "send_runtime_pdu.py"


def ensure_runtime_dirs() -> None:
    for path in (RUNTIME_DIR, RUNTIME_SEED_DIR, RUNTIME_PDU_DIR, RUNTIME_PCAP_DIR, RUNTIME_OAI_DIR):
        path.mkdir(parents=True, exist_ok=True)


def generate_real_seed_bundles() -> list[Path]:
    constraints = load_yaml(CONSTRAINTS_DIR / "messages.yaml")
    created: list[Path] = []
    for efsm_path in sorted(REAL_EFSM_DIR.glob("*.json")):
        bundle = generate_seeds_for_file(efsm_path, constraints)
        output_path = RUNTIME_SEED_DIR / efsm_path.name
        write_json(output_path, bundle)
        created.append(output_path)
    return created


def encode_seed(spec, seed: dict[str, object]) -> tuple[str, bytes] | None:
    payload = seed["payload"]
    if seed["message"] == "RRCSetupRequest":
        _, encoded, _ = build_setup_request(
            spec,
            int(payload.get("ue_Identity", 0) or 0),
            str(payload.get("establishmentCause", "mo_Data")),
        )
        return "RRCSetupRequest", encoded
    if "RRCResumeRequest" in seed["message"]:
        _, encoded, _ = build_resume_request(
            spec,
            int(payload.get("resumeIdentity", 0) or 0),
            str(payload.get("resumeCause", "mo_Data")),
        )
        return "RRCResumeRequest", encoded
    return None


def build_synthetic_pcap(seed: dict[str, object], encoded_payload: bytes, output_path: Path) -> dict[str, object]:
    metadata = f"{seed['procedure_id']}::{seed['id']}::{seed['message']}::{seed['mutation_class']}".encode()
    packet = (
        Ether(src="02:00:00:00:00:01", dst="02:00:00:00:00:02")
        / IP(src="192.0.2.10", dst="198.51.100.10")
        / UDP(sport=4999, dport=4999)
        / Raw(b"3GPPLAB\x00" + metadata + b"\x00" + encoded_payload)
    )
    wrpcap(str(output_path), [packet])
    return {
        "pcap": output_path.name,
        "udp_port": 4999,
        "encoded_size": len(encoded_payload),
    }


def write_compose_override() -> Path:
    override_path = RUNTIME_OAI_DIR / "docker-compose.runtime.yaml"
    write_text(
        override_path,
        f"""services:
  oai-gnb:
    volumes:
      - {RUNTIME_DIR}:/opt/3gpp-runtime:ro
  oai-nr-ue:
    volumes:
      - {RUNTIME_DIR}:/opt/3gpp-runtime:ro
  oai-nr-ue2:
    volumes:
      - {RUNTIME_DIR}:/opt/3gpp-runtime:ro
""",
    )
    return override_path


def write_replay_script(default_pdu: str | None) -> Path:
    script_path = RUNTIME_DIR / "replay_runtime.sh"
    fallback = f"$RUNTIME_DIR/pdus/{default_pdu}" if default_pdu else "$1"
    write_text(
        script_path,
        f"""#!/usr/bin/env bash
set -euo pipefail

RUNTIME_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
PDU_PATH="${{1:-{fallback}}}"

docker compose \\
  -f "{BASE_COMPOSE_PATH}" \\
  -f "$RUNTIME_DIR/oai/docker-compose.runtime.yaml" \\
  config --quiet

exec python3 "{UDP_INJECTOR_PATH}" "$PDU_PATH" --host "${{INJECT_HOST:-127.0.0.1}}" --port "${{INJECT_PORT:-4999}}"
""",
    )
    script_path.chmod(0o755)
    return script_path


def main() -> None:
    ensure_runtime_dirs()
    seed_paths = generate_real_seed_bundles()
    spec = compile_nr_rrc()

    runtime_manifest: list[dict[str, object]] = []
    default_pdu: str | None = None

    for seed_path in seed_paths:
        bundle = read_json(seed_path)
        for seed in bundle["seeds"]:
            encoded = encode_seed(spec, seed)
            record: dict[str, object] = {
                "seed_id": seed["id"],
                "procedure_id": seed["procedure_id"],
                "message": seed["message"],
                "mutation_class": seed["mutation_class"],
            }
            if encoded is not None:
                message_name, payload = encoded
                pdu_path = RUNTIME_PDU_DIR / f"{seed['id']}.uper.bin"
                pdu_path.write_bytes(payload)
                record["pdu_file"] = pdu_path.name
                record["encoded_hex"] = payload.hex()
                record["asn1_message"] = message_name
                pcap_path = RUNTIME_PCAP_DIR / f"{seed['id']}.pcap"
                record["pcap"] = build_synthetic_pcap(seed, payload, pcap_path)
                if default_pdu is None:
                    default_pdu = pdu_path.name

            runtime_manifest.append(record)

    override_path = write_compose_override()
    replay_script_path = write_replay_script(default_pdu)

    compose_check = subprocess.run(
        ["docker", "compose", "-f", str(BASE_COMPOSE_PATH), "-f", str(override_path), "config", "--quiet"],
        capture_output=True,
        text=True,
    )
    injector_check = subprocess.run(
        [
            "python3",
            str(UDP_INJECTOR_PATH),
            str(RUNTIME_PDU_DIR / default_pdu) if default_pdu else "/dev/null",
            "--host",
            "127.0.0.1",
            "--port",
            "4999",
        ],
        capture_output=True,
        text=True,
    )

    write_json(
        RUNTIME_DIR / "manifest.json",
        {
            "seed_files": sorted(path.name for path in seed_paths),
            "entry_count": len(runtime_manifest),
            "entries": runtime_manifest,
            "compose_override": override_path.name,
            "replay_script": replay_script_path.name,
            "compose_check": {
                "returncode": compose_check.returncode,
                "pass": compose_check.returncode == 0,
            },
            "udp_injector": {
                "returncode": injector_check.returncode,
                "pass": injector_check.returncode == 0,
            },
            "pass": compose_check.returncode == 0 and injector_check.returncode == 0,
        },
    )
    print(f"built runtime bundle in {RUNTIME_DIR} with {len(runtime_manifest)} entries")


if __name__ == "__main__":
    main()
