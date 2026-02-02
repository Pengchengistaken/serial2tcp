"""Configuration and command-line argument parsing for the serial-to-TCP bridge."""

import argparse


DEFAULT_PORT = "COM7"
DEFAULT_BAUD = 115200
DEFAULT_LISTEN = "0.0.0.0"
DEFAULT_TCP_PORT = 5000


def parse_args():
    """Parse command-line arguments and return a validated namespace."""
    parser = argparse.ArgumentParser(
        description="Bridge a local serial port (e.g. COM7) to a TCP server for remote access."
    )
    parser.add_argument(
        "--port",
        default=DEFAULT_PORT,
        help=f"Serial port name (default: {DEFAULT_PORT})",
    )
    parser.add_argument(
        "--baud",
        type=int,
        default=DEFAULT_BAUD,
        help=f"Baud rate (default: {DEFAULT_BAUD})",
    )
    parser.add_argument(
        "--listen",
        default=DEFAULT_LISTEN,
        help=f"TCP listen address (default: {DEFAULT_LISTEN})",
    )
    parser.add_argument(
        "--tcp-port",
        type=int,
        default=DEFAULT_TCP_PORT,
        help=f"TCP listen port (default: {DEFAULT_TCP_PORT})",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging (connection events, errors)",
    )
    args = parser.parse_args()
    _validate(args)
    return args


def _validate(args):
    """Validate parsed arguments; raise ValueError on invalid values."""
    if not (args.port and args.port.strip()):
        raise ValueError("Serial port (--port) must be non-empty")
    if args.baud <= 0:
        raise ValueError("Baud rate (--baud) must be positive")
    if not (1 <= args.tcp_port <= 65535):
        raise ValueError("TCP port (--tcp-port) must be between 1 and 65535")
