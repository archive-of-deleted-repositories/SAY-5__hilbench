from hilbench.dut import MotorControllerDUT, State


def test_ping_returns_pong():
    dut = MotorControllerDUT()
    assert dut.send("PING") == "OK PONG"


def test_run_cycle_transitions():
    dut = MotorControllerDUT()
    assert dut.send("ARM") == "OK armed"
    assert dut.state is State.ARMED
    assert dut.send("START") == "OK running"
    assert dut.send("SETSPEED 4200") == "OK speed=4200"
    assert dut.send("STATUS") == "OK state=RUNNING speed=4200"
    assert dut.send("STOP") == "OK stopped"
    assert dut.state is State.IDLE


def test_start_without_arm_is_rejected():
    dut = MotorControllerDUT()
    assert dut.send("START") == "ERR not_armed"


def test_out_of_range_speed_faults():
    dut = MotorControllerDUT()
    dut.send("ARM")
    dut.send("START")
    assert dut.send("SETSPEED 99999") == "ERR out_of_range"
    assert dut.state is State.FAULT
    assert dut.send("ARM") == "ERR in_fault"
    assert dut.send("RESET") == "OK reset"
    assert dut.state is State.IDLE


def test_unknown_command():
    dut = MotorControllerDUT()
    assert dut.send("FLY").startswith("ERR unknown_command")
