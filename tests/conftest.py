import os
import time
from pathlib import Path
import pytest
from tests.harness.runtime import harness


@pytest.fixture
def system(request):
    root = Path(os.environ.get("MS2_EVIDENCE_DIR", "results/latest-tests"))
    with harness(root / request.node.name) as instance:
        yield instance


def pytest_sessionfinish(session, exitstatus):
    required = os.environ.get("MS2_REQUIRE_XFAIL")
    if required is not None and not session.config.option.runxfail:
        reporter = session.config.pluginmanager.get_plugin("terminalreporter")
        count = len(reporter.stats.get("xfailed", []))
        if count != int(required):
            reporter.write_sep("!", f"MS2 requires {required} intentional XFAIL; observed {count}")
            session.exitstatus = pytest.ExitCode.TESTS_FAILED
