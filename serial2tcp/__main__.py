"""Entry point: parse config and run the serial-to-TCP bridge with graceful shutdown."""

import sys

from serial2tcp.config import parse_args
from serial2tcp.bridge import run_bridge


def main():
    try:
        args = parse_args()
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    try:
        run_bridge(
            port=args.port,
            baud=args.baud,
            listen=args.listen,
            tcp_port=args.tcp_port,
            verbose=args.verbose,
        )
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
