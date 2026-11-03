"""Check the post-deploy smoke test, partly against the API served locally."""

import importlib.util
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
SCRIPT = ROOT / "scripts" / "smoke_test_api.py"

spec = importlib.util.spec_from_file_location("smoke_test_api", SCRIPT)
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)

RESULT = {"income": [0, 1]}


def test_a_computed_stream_returns_its_answer():
    events = [{"step": "setup"}, {"step": "baseline"}, {"step": "complete", "result": RESULT}]
    assert smoke.read_stream(events) == (True, RESULT)


def test_a_cached_stream_says_so():
    events = [{"step": "cached"}, {"step": "complete", "result": RESULT}]
    assert smoke.read_stream(events) == (False, RESULT)


def test_an_error_event_fails_although_the_status_is_200():
    events = [{"step": "setup"}, {"step": "error", "error": "Could not find the parameter"}]
    with pytest.raises(SystemExit, match="Could not find the parameter"):
        smoke.read_stream(events)


def test_a_stream_that_stops_early_fails():
    with pytest.raises(SystemExit, match="without a result"):
        smoke.read_stream([{"step": "setup"}, {"step": "baseline"}])


def test_the_calculator_checks_skip_the_explain_household():
    assert smoke.HOUSEHOLD["age_head"] not in smoke.AGES
    assert len(smoke.AGES) > smoke.STREAM_TRIES


@pytest.fixture(scope="module")
def local_api():
    """Serve this checkout's API on a free local port, as uvicorn does on Modal."""
    uvicorn = pytest.importorskip("uvicorn")
    from src.aca_api import api

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    server = uvicorn.Server(
        uvicorn.Config(api.app, host="127.0.0.1", port=port, log_level="warning")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 60
    while not server.started:
        assert thread.is_alive() and time.monotonic() < deadline, "the API didn't start"
        time.sleep(0.1)
    yield api, f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=30)


def test_the_smoke_test_passes_against_this_code(local_api):
    _, url = local_api
    run = subprocess.run(
        [sys.executable, str(SCRIPT), url], capture_output=True, text=True, timeout=900
    )
    assert run.returncode == 0, run.stdout + run.stderr
    assert "ok /api/calculate-stream (age " in run.stdout
    assert "ok /api/calculate (age " in run.stdout


def test_the_stream_check_moves_past_cached_answers(local_api, capsys):
    api, url = local_api
    api._local_calculation_cache.clear()
    smoke.check_calculate_stream(url, [40])
    with pytest.raises(SystemExit, match="all came from the cache"):
        smoke.check_calculate_stream(url, [40])
    smoke.check_calculate_stream(url, [40, 41])
    assert "(age 41)" in capsys.readouterr().out
