"""Simulated device under test.

The DUT is a deterministic motor controller modeled as a state machine. It
accepts text commands and returns text responses. Each command carries a small,
deterministic processing delay so that the runner can measure per step latency
against timing budgets. The delay is configurable to support jitter injection in
tests without touching the protocol.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum


class State(str, Enum):
    """Operating states of the motor controller."""

    IDLE = "IDLE"
    ARMED = "ARMED"
    RUNNING = "RUNNING"
    FAULT = "FAULT"


# Per command nominal service time in seconds. These model the time the device
# spends handling a command and are the basis for timing budget assertions.
DEFAULT_SERVICE_TIME = {
    "PING": 0.0005,
    "STATUS": 0.0005,
    "ARM": 0.002,
    "START": 0.003,
    "STOP": 0.002,
    "SETSPEED": 0.001,
    "RESET": 0.002,
}


@dataclass
class MotorControllerDUT:
    """A deterministic motor controller simulator.

    Commands are space separated: a verb followed by optional arguments.
    Responses are either ``OK`` with optional payload or ``ERR`` with a reason.
    A monotonically advancing virtual clock is not used; real wall time is spent
    via ``sleep`` so that timing capture exercises the same path as a real
    transport would.
    """

    state: State = State.IDLE
    speed: int = 0
    max_speed: int = 10000
    service_time: dict[str, float] = field(
        default_factory=lambda: dict(DEFAULT_SERVICE_TIME)
    )
    # Extra latency added to every command, used to model a slow or loaded
    # device. Tests inject jitter through this hook.
    latency_offset: float = 0.0
    _sleep: Callable[[float], None] = field(default=time.sleep, repr=False)

    def send(self, command: str) -> str:
        """Process one command and return the response string."""
        verb, *args = command.strip().split()
        verb = verb.upper()
        self._spend(verb)
        handler: Callable[[list[str]], str] | None = getattr(
            self, f"_cmd_{verb.lower()}", None
        )
        if handler is None:
            return f"ERR unknown_command {verb}"
        return handler(args)

    def _spend(self, verb: str) -> None:
        delay = self.service_time.get(verb, 0.0005) + self.latency_offset
        if delay > 0:
            self._sleep(delay)

    def _cmd_ping(self, args: list[str]) -> str:
        return "OK PONG"

    def _cmd_status(self, args: list[str]) -> str:
        return f"OK state={self.state.value} speed={self.speed}"

    def _cmd_arm(self, args: list[str]) -> str:
        if self.state is State.FAULT:
            return "ERR in_fault"
        if self.state is State.RUNNING:
            return "ERR running"
        self.state = State.ARMED
        return "OK armed"

    def _cmd_start(self, args: list[str]) -> str:
        if self.state is not State.ARMED:
            return "ERR not_armed"
        self.state = State.RUNNING
        return "OK running"

    def _cmd_stop(self, args: list[str]) -> str:
        if self.state is not State.RUNNING:
            return "ERR not_running"
        self.state = State.IDLE
        self.speed = 0
        return "OK stopped"

    def _cmd_setspeed(self, args: list[str]) -> str:
        if not args:
            return "ERR missing_argument"
        try:
            value = int(args[0])
        except ValueError:
            return "ERR bad_argument"
        if value < 0 or value > self.max_speed:
            self.state = State.FAULT
            return "ERR out_of_range"
        if self.state is not State.RUNNING:
            return "ERR not_running"
        self.speed = value
        return f"OK speed={self.speed}"

    def _cmd_reset(self, args: list[str]) -> str:
        self.state = State.IDLE
        self.speed = 0
        return "OK reset"
