import json
import os
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path
import pytest
from tests.harness.runtime import harness


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    setattr(item, "rep_" + report.when, report)


def java_version():
    try:
        out = subprocess.run([os.environ.get("JAVA", "java"), "-version"], capture_output=True, text=True, timeout=20)
        return (out.stderr or out.stdout).splitlines()[0]
    except (OSError, IndexError, subprocess.SubprocessError):
        return None


@pytest.fixture
def system(request):
    root = Path(os.environ.get("MS2_EVIDENCE_DIR", "results/latest-tests"))
    directory = root / request.node.name
    started = datetime.now(timezone.utc).isoformat()
    instance = None
    try:
        with harness(directory) as instance:
            yield instance
    finally:
        # Written for passing and failing tests alike, after the harness exported evidence and tore down.
        call = getattr(request.node, "rep_call", None)
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "metadata.json").write_text(json.dumps({
            "schema_version": 1, "test": request.node.nodeid,
            "outcome": call.outcome if call else "not-run", "xfail": bool(call is not None and hasattr(call, "wasxfail")),
            "backend": os.environ.get("MS2_BACKEND", "native"),
            "scheduler_run_id": getattr(getattr(instance, "api", None), "run_id", None),
            "source_revision": os.environ.get("MS2_SOURCE_REV"),
            "started_utc": started, "finished_utc": datetime.now(timezone.utc).isoformat(),
            "python": platform.python_version(), "java": java_version(), "platform": platform.platform()}, indent=2))


def pytest_sessionfinish(session, exitstatus):
    required = os.environ.get("MS2_REQUIRE_XFAIL")
    if required is not None and not session.config.option.runxfail:
        reporter = session.config.pluginmanager.get_plugin("terminalreporter")
        count = len(reporter.stats.get("xfailed", []))
        if count != int(required):
            reporter.write_sep("!", f"MS2 requires {required} intentional XFAIL; observed {count}")
            session.exitstatus = pytest.ExitCode.TESTS_FAILED
