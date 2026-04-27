import pathlib
import sys


sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from models.simulation import Simulation


def test_current_state_is_available_before_first_recorded_step():
    simulation = Simulation([], [], [])

    state = simulation.get_current_state()

    assert state["step"] == 0
    assert state["running"] is False
    assert state["evs"] == []
    assert state["stations"] == []
    assert state["metrics"]["max_queue_length"] == 0


def test_step_handles_empty_station_list():
    simulation = Simulation([], [], [])

    simulation.step()

    assert simulation.current_step == 1
    assert simulation.metrics["max_queue_length"] == 0
