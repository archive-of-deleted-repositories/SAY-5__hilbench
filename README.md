# HILBench

HILBench is a hardware-in-the-loop (HIL) test automation framework. It drives a
simulated device under test (DUT) through scripted scenarios, captures responses
and per step latency, asserts against expected behavior and timing budgets, and
writes structured pass/fail reports that a CI pipeline ingests on every change.

The simulated DUT stands in for real hardware so the whole suite runs hermetically
in CI with no bench attached. Swapping the in process transport for the TCP
transport lets the same scenarios run against a DUT on the other end of a socket.

## What is in the box

- A deterministic DUT simulator: a motor controller modeled as a state machine
  (`IDLE`, `ARMED`, `RUNNING`, `FAULT`) that accepts text commands and emits
  responses with a configurable per command service time.
- Two transports with a shared interface: in process (direct call) and TCP
  (newline delimited protocol against `hilbench.server`).
- A scenario format in YAML: a named list of steps, each sending a command and
  optionally asserting on the response value, a substring, and a latency budget.
- A runner that measures per step latency with a monotonic clock and evaluates
  value and timing assertions.
- Report writers: JSON, JUnit XML for CI ingestion, and a human readable summary.

## Install

```
pip install -e ".[dev]"
```

## Run the bundled scenarios

```
hilbench scenarios/ --json report.json --junit report.xml
```

The command exits non zero if any step fails, which fails the CI build. The
JUnit XML is ingested by the CI run and the JSON report is uploaded as an
artifact.

## A scenario

```yaml
name: run_cycle
description: Arm, start, set speed, then stop the controller and verify state.
steps:
  - name: arm
    command: ARM
    expect: OK armed
    max_latency_ms: 50
  - name: start
    command: START
    expect: OK running
    max_latency_ms: 50
  - name: set_speed
    command: SETSPEED 4200
    expect: OK speed=4200
    max_latency_ms: 50
```

Each step can use `expect` (exact match), `expect_contains` (substring), and
`max_latency_ms` (a timing budget). A step fails on a wrong value or a response
that arrives later than its budget, so timing regressions surface as failures
rather than passing silently.

## Docker

```
docker build -t hilbench .
docker run --rm hilbench scenarios/ --json report.json --junit report.xml
```

`docker-compose.yml` brings up the DUT as a TCP server and a runner alongside it.

## Protocol

Commands are space separated: a verb and optional arguments. Responses begin
with `OK` (with optional payload) or `ERR` (with a reason).

| Command          | Effect                                   | Response               |
|------------------|------------------------------------------|------------------------|
| `PING`           | liveness                                 | `OK PONG`              |
| `STATUS`         | report state and speed                   | `OK state=... speed=...` |
| `ARM`            | move from `IDLE` to `ARMED`              | `OK armed`             |
| `START`          | move from `ARMED` to `RUNNING`           | `OK running`           |
| `SETSPEED <n>`   | set speed while running                  | `OK speed=<n>`         |
| `STOP`           | move to `IDLE`, clear speed              | `OK stopped`           |
| `RESET`          | return to `IDLE` from any state          | `OK reset`             |

An out of range `SETSPEED` drives the controller into `FAULT`; `RESET` recovers.

## Throughput benchmark

`benchmarks/throughput.py` builds a large scenario batch and measures how many
steps per second the runner drives against the in process DUT with modeled
service times removed, so the number reflects framework overhead. On a local run
at 200 scenarios of 50 steps each (10000 steps), the best of seven repeats was
about 1.03 million steps per second.

```
python -m benchmarks.throughput --scenarios 200 --steps 50 --repeats 7
```

CI runs `benchmarks/check_regression.py` as a smoke gate. It measures throughput
and fails if it falls below a conservative floor by more than 30 percent. The
floor is set well under the local figure to absorb shared runner variance, so the
gate catches a real regression without flaking on noise.

## How this differs

HILBench is a generic HIL framework: a scenario format, a simulated DUT, timing
budget assertions, and a JUnit-into-CI gate. The angle is the scenario DSL plus
timing budget assertions wired into CI as ingested test results.

- `mfg-test-controller` is a Modbus/TCP test station for one specific protocol.
  HILBench is protocol agnostic at the scenario layer and ships a simulated DUT
  so the suite runs without hardware.
- `tracesift` analyzes failures after the fact. HILBench runs the scenarios that
  produce the pass/fail and timing data in the first place.

## License

MIT. See [LICENSE](LICENSE).
