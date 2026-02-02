"""Asyncio-based bridge between a serial port and a single TCP client."""

import asyncio
import logging
from typing import Optional

import serial

logger = logging.getLogger("serial2tcp")


def open_serial(port: str, baud: int) -> serial.Serial:
    """Open the serial port with the given settings."""
    return serial.Serial(port=port, baudrate=baud)


async def bridge_serial_to_tcp(ser: serial.Serial, writer: asyncio.StreamWriter):
    """Read from serial and write to TCP until serial is closed or writer fails."""
    try:
        while True:
            n = ser.in_waiting
            if n > 0:
                data = await asyncio.to_thread(ser.read, n)
                if not data:
                    break
                writer.write(data)
                await writer.drain()
            else:
                await asyncio.sleep(0.01)
    except (ConnectionResetError, BrokenPipeError, asyncio.CancelledError):
        pass
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


async def bridge_tcp_to_serial(ser: serial.Serial, reader: asyncio.StreamReader):
    """Read from TCP and write to serial until reader is closed or serial fails."""
    try:
        while True:
            data = await reader.read(4096)
            if not data:
                break
            await asyncio.to_thread(ser.write, data)
    except (ConnectionResetError, BrokenPipeError, asyncio.CancelledError):
        pass


async def handle_client(
    ser: serial.Serial,
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    verbose: bool = False,
):
    """Run bidirectional bridge for one TCP client; single-client: one at a time."""
    peer = writer.get_extra_info("peername", ("?", "?"))
    if verbose:
        logger.info("TCP client connected: %s:%s", peer[0], peer[1])
    task_a = asyncio.create_task(bridge_serial_to_tcp(ser, writer))
    task_b = asyncio.create_task(bridge_tcp_to_serial(ser, reader))
    try:
        await asyncio.gather(task_a, task_b)
    finally:
        if verbose:
            logger.info("TCP client disconnected: %s:%s", peer[0], peer[1])
        task_a.cancel()
        task_b.cancel()
        try:
            await asyncio.gather(task_a, task_b, return_exceptions=True)
        except Exception:
            pass


async def run_bridge_async(
    port: str, baud: int, listen: str, tcp_port: int, verbose: bool = False
):
    """Open serial port, start TCP server, and accept one client at a time."""
    ser = open_serial(port, baud)
    if verbose:
        logger.info("Serial opened: %s @ %s baud", port, baud)
    current_client: Optional[asyncio.StreamWriter] = None

    async def on_connect(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        nonlocal current_client
        if current_client is not None:
            if verbose:
                logger.warning("Rejecting new connection (single client only)")
            writer.close()
            await writer.wait_closed()
            return
        current_client = writer
        try:
            await handle_client(ser, reader, writer, verbose=verbose)
        finally:
            current_client = None

    server = await asyncio.start_server(on_connect, listen, tcp_port)
    if verbose:
        logger.info("TCP server listening on %s:%s", listen, tcp_port)
    try:
        async with server:
            await server.serve_forever()
    finally:
        ser.close()
        if verbose:
            logger.info("Serial closed")


def run_bridge(
    port: str,
    baud: int,
    listen: str,
    tcp_port: int,
    verbose: bool = False,
):
    """Synchronous entry: run the asyncio bridge until interrupted."""
    if verbose:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    try:
        asyncio.run(run_bridge_async(port, baud, listen, tcp_port, verbose=verbose))
    except KeyboardInterrupt:
        pass
