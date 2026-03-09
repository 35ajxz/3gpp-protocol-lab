from __future__ import annotations

import argparse
from pathlib import Path
import socket


def main() -> None:
    parser = argparse.ArgumentParser(description="Send a generated UPER PDU over UDP.")
    parser.add_argument("pdu_path", help="path to a .uper.bin file")
    parser.add_argument("--host", default="127.0.0.1", help="target host")
    parser.add_argument("--port", type=int, default=4999, help="target UDP port")
    parser.add_argument("--repeat", type=int, default=1, help="number of UDP sends")
    args = parser.parse_args()

    payload = Path(args.pdu_path).read_bytes()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        for _ in range(args.repeat):
            sock.sendto(payload, (args.host, args.port))
    finally:
        sock.close()
    print(f"sent {len(payload)} bytes to {args.host}:{args.port} from {Path(args.pdu_path).name}")


if __name__ == "__main__":
    main()
