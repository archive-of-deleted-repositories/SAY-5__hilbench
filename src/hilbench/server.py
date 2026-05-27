"""A small TCP server that exposes a DUT over the newline delimited protocol.

This lets the runner exercise the DUT across a real socket, which is closer to a
bench setup where the device sits on the other end of a link. It is single
client and single threaded by design, which keeps timing deterministic.
"""

from __future__ import annotations

import argparse
import socketserver

from hilbench.dut import MotorControllerDUT


class _Handler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        dut = MotorControllerDUT()
        for raw in self.rfile:
            command = raw.decode("utf-8").rstrip("\n")
            if not command:
                continue
            response = dut.send(command)
            self.wfile.write((response + "\n").encode("utf-8"))


def serve(host: str, port: int) -> None:
    with socketserver.TCPServer((host, port), _Handler) as server:
        server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the DUT TCP server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9099)
    args = parser.parse_args()
    serve(args.host, args.port)


if __name__ == "__main__":
    main()
