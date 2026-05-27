"""HILBench: a hardware-in-the-loop test automation framework."""

from hilbench.dut import MotorControllerDUT
from hilbench.robust import FlakeReport, RetryPolicy, detect_flake
from hilbench.transport import InProcessTransport, Transport

__version__ = "0.1.0"

__all__ = [
    "MotorControllerDUT",
    "InProcessTransport",
    "Transport",
    "RetryPolicy",
    "FlakeReport",
    "detect_flake",
]
