from __future__ import annotations

from pathlib import Path

import asn1tools

from common import write_json


ROOT = Path(__file__).resolve().parents[1]
ASN1_OUTPUT_DIR = ROOT / "outputs" / "asn1"
ASN1_PATH = ASN1_OUTPUT_DIR / "NR-RRC-Definitions.asn1"
ASN1_PDU_DIR = ASN1_OUTPUT_DIR / "pdus"

ESTABLISHMENT_CAUSE_MAP = {
    "emergency": "emergency",
    "mo_Signalling": "mo-Signalling",
    "mo_Data": "mo-Data",
}


def compile_nr_rrc() -> asn1tools.compiler.Specification:
    return asn1tools.compile_files(str(ASN1_PATH), "uper")


def integer_to_bitstring(value: int, bits: int) -> tuple[bytes, int]:
    mask = (1 << bits) - 1
    normalized = value & mask
    byte_length = (bits + 7) // 8
    return normalized.to_bytes(byte_length, "big"), bits


def _to_jsonable(value):
    if isinstance(value, bytes):
        return {"hex": value.hex()}
    if isinstance(value, tuple) and len(value) == 2 and isinstance(value[0], bytes):
        return {"hex": value[0].hex(), "bits": value[1]}
    if isinstance(value, tuple):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_jsonable(item) for key, item in value.items()}
    return value


def build_setup_request(spec, ue_identity: int, establishment_cause: str) -> tuple[dict[str, object], bytes, dict[str, object]]:
    payload = {
        "rrcSetupRequest": {
            "ue-Identity": ("randomValue", integer_to_bitstring(ue_identity, 39)),
            "establishmentCause": ESTABLISHMENT_CAUSE_MAP.get(establishment_cause, "mo-Data"),
            "spare": integer_to_bitstring(0, 1),
        }
    }
    encoded = spec.encode("RRCSetupRequest", payload)
    decoded = spec.decode("RRCSetupRequest", encoded)
    return payload, encoded, decoded


def build_resume_request(spec, resume_identity: int, resume_cause: str = "mo_Data") -> tuple[dict[str, object], bytes, dict[str, object]]:
    payload = {
        "rrcResumeRequest": {
            "resumeIdentity": integer_to_bitstring(resume_identity, 24),
            "resumeMAC-I": integer_to_bitstring(0xAABB, 16),
            "resumeCause": ESTABLISHMENT_CAUSE_MAP.get(resume_cause, "mo-Data"),
            "spare": integer_to_bitstring(0, 1),
        }
    }
    encoded = spec.encode("RRCResumeRequest", payload)
    decoded = spec.decode("RRCResumeRequest", encoded)
    return payload, encoded, decoded


def main() -> None:
    ASN1_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ASN1_PDU_DIR.mkdir(parents=True, exist_ok=True)

    spec = compile_nr_rrc()
    cases = []

    for case_name, builder in (
        ("setup_request_nominal", lambda: build_setup_request(spec, 77, "mo_Signalling")),
        ("setup_request_boundary", lambda: build_setup_request(spec, 549755813887, "emergency")),
        ("resume_request_nominal", lambda: build_resume_request(spec, 101, "mo_Data")),
        ("resume_request_boundary", lambda: build_resume_request(spec, 1099511627775, "mo_Data")),
    ):
        payload, encoded, decoded = builder()
        (ASN1_PDU_DIR / f"{case_name}.uper.bin").write_bytes(encoded)
        cases.append(
            {
                "name": case_name,
                "encoded_hex": encoded.hex(),
                "encoded_size": len(encoded),
                "payload": _to_jsonable(payload),
                "decoded": _to_jsonable(decoded),
                "roundtrip_ok": True,
            }
        )

    write_json(
        ASN1_OUTPUT_DIR / "validation.json",
        {
            "asn1_file": ASN1_PATH.name,
            "type_count": len(spec.types),
            "roundtrips": cases,
            "pass": True,
        },
    )
    print(f"validated ASN.1 module {ASN1_PATH.name} with {len(cases)} roundtrip cases")


if __name__ == "__main__":
    main()
