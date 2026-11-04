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

# Every single adult with the smoke test's county and scenarios: the households
# whose cached answers could stand in for one the deployed code computes.
SINGLE_ADULTS = [{**smoke.HOUSEHOLD, "age_head": age} for age in range(18, 101)]


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


# An answer that passes every check in check_result.
HEALTHY_ANSWER = {
    "income": [0.0, 1.0],
    "ptc_baseline": [1.0, 0.0],
    "ptc_700fpl": [1.0, 0.0],
    "fpl": 1.0,
    "slcsp": 1.0,
}


def test_the_result_check_passes_a_healthy_answer():
    smoke.check_result("answer", HEALTHY_ANSWER)


@pytest.mark.parametrize(
    "change, message",
    [
        ({"income": [0.0]}, "income has 1 points"),
        ({"ptc_baseline": [1.0]}, "ptc_baseline has 1 points"),
        ({"ptc_baseline": [1.0, -1.0]}, "ptc_baseline has a negative"),
        ({"ptc_700fpl": [1.0, float("nan")]}, "ptc_700fpl has a negative or non-finite"),
        ({"fpl": 0.0}, r"\(0\.0, 1\.0\)"),
        ({"slcsp": 0.0}, r"\(1\.0, 0\.0\)"),
        ({"ptc_baseline": [0.0, 0.0]}, "baseline PTC is zero"),
        ({"ptc_700fpl": [0.0, 0.0]}, "700% FPL PTC is zero"),
    ],
)
def test_the_result_check_rejects_a_wrong_answer(change, message):
    with pytest.raises(AssertionError, match=message):
        smoke.check_result("answer", {**HEALTHY_ANSWER, **change})


def test_an_answer_must_name_the_commit(monkeypatch):
    monkeypatch.setattr(smoke, "COMMIT", "this")
    smoke.check_commit({"X-ACA-API-Commit": "this"})
    with pytest.raises(smoke.OtherVersion, match="commit previous"):
        smoke.check_commit({"X-ACA-API-Commit": "previous"})
    # Code from before the header existed sends none.
    with pytest.raises(smoke.OtherVersion, match="names no commit"):
        smoke.check_commit({})


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


@pytest.fixture
def poisoned_cache(local_api):
    """Cache a wrong answer, zero credits everywhere, for every single adult."""
    api, _ = local_api
    from src.aca_api.models import CalculateRequest, CalculateResponse

    zeros = [0.0, 0.0]
    wrong = CalculateResponse(
        income=[0.0, 1.0],
        ptc_baseline=zeros,
        ptc_ira=zeros,
        ptc_700fpl=zeros,
        ptc_additional_bracket=zeros,
        ptc_simplified_bracket=zeros,
        fpl=1.0,
        slcsp=1.0,
        medicaid=zeros,
        chip=zeros,
    )
    api._local_calculation_cache.clear()
    for household in SINGLE_ADULTS:
        key = api.get_cache_key(CalculateRequest(**household))
        api._local_calculation_cache[key] = wrong
    yield wrong
    api._local_calculation_cache.clear()


def test_the_smoke_test_passes_against_this_code(local_api, poisoned_cache):
    # The checks pass only if the code computes its own answers instead of
    # returning the wrong ones in the cache.
    _, url = local_api
    run = subprocess.run(
        [sys.executable, str(SCRIPT), url], capture_output=True, text=True, timeout=900
    )
    assert run.returncode == 0, run.stdout + run.stderr
    assert "ok /api/calculate-stream:" in run.stdout
    assert "ok /api/calculate:" in run.stdout


def test_skipping_the_cache_computes_without_storing(local_api, poisoned_cache):
    api, url = local_api
    before = dict(api._local_calculation_cache)
    wrong = poisoned_cache.model_dump()
    stream_url, calculate_url = f"{url}/api/calculate-stream", f"{url}/api/calculate"
    # A plain request gets the cached answer from either endpoint...
    assert smoke.read_stream(smoke.stream_events(stream_url, smoke.HOUSEHOLD)) == (False, wrong)
    assert smoke.call(calculate_url, smoke.HOUSEHOLD) == wrong
    # ...and one that skips the cache gets the same new answer from both,
    # leaving the cache as it was.
    computed, streamed = smoke.read_stream(smoke.stream_events(stream_url, smoke.FRESH))
    assert computed
    smoke.check_result("stream", streamed)
    assert smoke.call(calculate_url, smoke.FRESH) == streamed
    assert dict(api._local_calculation_cache) == before


def test_the_stream_check_fails_on_a_cached_answer(local_api, poisoned_cache):
    # An API that predates skip_cache ignores it and answers like this.
    _, url = local_api
    with pytest.raises(SystemExit, match="answered from the cache"):
        smoke.check_calculate_stream(url, smoke.HOUSEHOLD)


def test_every_response_is_checked_for_the_commit(local_api, poisoned_cache, monkeypatch):
    # Cached answers keep these requests quick; invalid ones return 422.
    _, url = local_api
    monkeypatch.setenv("ACA_API_COMMIT", "previous")
    monkeypatch.setattr(smoke, "COMMIT", "this")
    stream_url, calculate_url = f"{url}/api/calculate-stream", f"{url}/api/calculate"
    invalid = {**smoke.HOUSEHOLD, "state": "XX"}
    for request in (
        lambda: smoke.call(f"{url}/api/health"),
        lambda: smoke.call(calculate_url, smoke.HOUSEHOLD),
        lambda: smoke.call(calculate_url, invalid),
        lambda: smoke.read_stream(smoke.stream_events(stream_url, smoke.HOUSEHOLD)),
        lambda: smoke.read_stream(smoke.stream_events(stream_url, invalid)),
    ):
        with pytest.raises(smoke.OtherVersion, match="commit previous"):
            request()


def test_the_checks_wait_for_this_deploy(local_api, monkeypatch):
    # The previous commit answers first, as during Modal's handover to a new
    # version, and this one from the first retry.
    _, url = local_api
    monkeypatch.setenv("ACA_API_COMMIT", "previous")
    run = subprocess.Popen(
        [sys.executable, str(SCRIPT), url, "--commit", "this", "--wait", "60"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    first = run.stdout.readline()
    monkeypatch.setenv("ACA_API_COMMIT", "this")
    out, err = run.communicate(timeout=900)
    assert first.startswith("waiting: commit previous answered check_health"), first + out + err
    assert run.returncode == 0, first + out + err
    assert "ok /api/calculate-stream:" in out and "ok /api/calculate:" in out


def test_the_checks_fail_if_this_deploy_never_answers(local_api, monkeypatch):
    _, url = local_api
    monkeypatch.setenv("ACA_API_COMMIT", "previous")
    run = subprocess.run(
        [sys.executable, str(SCRIPT), url, "--commit", "this", "--wait", "6"],
        capture_output=True, text=True, timeout=120,
    )
    assert run.returncode == 1, run.stdout + run.stderr
    assert "check_health: commit previous still answered after 6 s" in run.stderr
