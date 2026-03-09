#!/usr/bin/env bash
set -euo pipefail

RUNTIME_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PDU_PATH="${1:-$RUNTIME_DIR/pdus/5.3.13-step-3-nominal.uper.bin}"

docker compose \
  -f "/home/huazi4ai/3gpp-protocol-lab/targets/oai/docker-compose.yaml" \
  -f "$RUNTIME_DIR/oai/docker-compose.runtime.yaml" \
  config --quiet

exec python3 "/home/huazi4ai/3gpp-protocol-lab/scripts/send_runtime_pdu.py" "$PDU_PATH" --host "${INJECT_HOST:-127.0.0.1}" --port "${INJECT_PORT:-4999}"
