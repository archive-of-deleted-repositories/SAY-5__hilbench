"""Transports that carry commands to a DUT.

Two transports are provided: an in process transport that calls the simulator
directly, and a TCP transport that speaks a newline delimited protocol to a DUT
server. Both implement the same ``send`` method so the runner is agnostic to
which is used.
"""

from __future__ import annotations

import socket
from typing import Protocol, runtime_checkable

from hilbench.dut import MotorControllerDUT


@runtime_checkable
class Transport(Protocol):
    """Carries a command string to a DUT and returns the response string."""

    def send(self, command: str) -> str: ...

    def close(self) -> None: ...


class InProcessTransport:
    """Calls a simulator instance directly within the same process."""

    def __init__(self, dut: MotorControllerDUT | None = None) -> None:
        self.dut = dut if dut is not None else MotorControllerDUT()

    def send(self, command: str) -> str:
        return self.dut.send(command)

    def close(self) -> None:
        return None


class TCPTransport:
    """Sends newline delimited commands to a DUT server over TCP."""

    def __init__(self, host: str, port: int, timeout: float = 2.0) -> None:
        self._sock = socket.create_connection((host, port), timeout=timeout)
        self._reader = self._sock.makefile("r", encoding="utf-8", newline="\n")

    def send(self, command: str) -> str:
        self._sock.sendall((command.strip() + "\n").encode("utf-8"))
        line = self._reader.readline()
        return line.rstrip("\n")

    def close(self) -> None:
        try:
            self._reader.close()
        finally:
            self._sock.close()
