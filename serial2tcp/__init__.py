"""Serial-to-TCP bridge: expose a local serial port (e.g. COM7) as a TCP server."""

from serial2tcp.bridge import run_bridge

__all__ = ["run_bridge"]
