"""Build a small flat ConfigMap payload for the pinned `hokea test` runner.

This does not contact Docker, Kubernetes, a registry, or GitHub. Correctness tests
are shipped byte-for-byte and imported, never copied into a second oracle.
"""
import argparse
import base64
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUDGET = 900_000  # Pinned hokea.runner.CONFIGMAP_BUDGET, text bytes on the wire.
FILES = [
    "tests/__init__.py", "tests/conftest.py", "tests/harness/__init__.py",
    "tests/harness/api.py", "tests/harness/runtime.py", "tests/harness/hokea_adapter.py",
    "tests/harness/check_evidence.py", "tests/faults/test_worker_crash.py",
    "tests/integration/test_functional_workload.py", "tests/integration/test_hokea_smoke.py",
    "workloads/functional/functional.json", "workloads/functional/expected.json",
    "deploy/hokea/HOKEA_API_SHA256.json",
]

BOOTSTRAP = '''"""Unpack exact project bytes inside Hokea's writable /project."""
import base64
import hashlib
import json
import os
import sys
from pathlib import Path

here = Path(__file__).resolve().parent
payload = json.loads((here / "payload.json").read_text())
project = here / "_project"
for name, item in payload["files"].items():
    relative = Path(name)
    if relative.is_absolute() or ".." in relative.parts:
        raise RuntimeError("Unsafe payload path")
    raw = base64.b64decode(item["base64"], validate=True)
    if hashlib.sha256(raw).hexdigest() != item["sha256"]:
        raise RuntimeError("Payload checksum mismatch: " + name)
    path = project / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
sys.path.insert(0, str(project))
os.environ.update(payload["environment"])
if "--collect-only" in sys.argv or "--co" in sys.argv:
    # Collection does not execute the fault oracle. Execution always requires one XFAIL.
    os.environ.pop("MS2_REQUIRE_XFAIL", None)
os.environ["MS2_EVIDENCE_DIR"] = str(here / "runs")
pytest_plugins = ["tests.conftest"]
'''
ENTRY = '''"""Import the accepted oracles; no Hokea-specific scheduling assertions."""
from tests.integration.test_hokea_smoke import test_service_exchange
from tests.integration.test_functional_workload import test_committed_functional_workload
from tests.faults.test_worker_crash import test_worker_crash_reassignment
'''
INI = '''[pytest]
testpaths = test_entry.py
addopts = -ra --strict-markers
xfail_strict = true
markers =
    intentional_ms2: the one narrowly scoped worker-crash liveness oracle
'''


def build(output, images, source_revision, *, root=ROOT, allow_preloaded_tags=False):
    if not source_revision or any(c.isspace() for c in source_revision):
        raise ValueError("A nonempty source identifier without whitespace is required")
    env = {"MS2_BACKEND": "hokea", "MS2_HOKEA_RUNTIME": "kubernetes",
           "MS2_REQUIRE_XFAIL": "1", "MS2_SOURCE_REV": source_revision}
    for role in ["scheduler", "artifact-store", "worker"]:
        image = images[role]
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9./_:@-]*", image):
            raise ValueError("Invalid image reference")
        if not allow_preloaded_tags and not re.fullmatch(r".+@sha256:[0-9a-f]{64}", image):
            raise ValueError("Use immutable image digests or explicitly acknowledge staff-preloaded tags")
        env["MS2_HOKEA_" + role.upper().replace("-", "_") + "_IMAGE"] = image
    files = {}
    for name in FILES:
        raw = (Path(root) / name).read_bytes()
        files[name] = {"sha256": hashlib.sha256(raw).hexdigest(), "base64": base64.b64encode(raw).decode()}
    payload = json.dumps({"schema_version": 1, "environment": env, "files": files}, sort_keys=True, indent=2)
    shipped = {"payload.json": payload, "conftest.py": BOOTSTRAP, "test_entry.py": ENTRY, "pytest.ini": INI}
    size = sum(len(text.encode()) for text in shipped.values())
    if size > BUDGET:
        raise ValueError(f"Runner package costs {size} bytes; pinned ConfigMap budget is {BUDGET}")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)  # Never replace a prior package/run.
    for name, content in shipped.items():
        (output / name).write_text(content)
    return {"bytes": size, "budget": BUDGET, "files": sorted(shipped), "source_revision": source_revision}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--scheduler-image", required=True)
    parser.add_argument("--artifact-store-image", required=True)
    parser.add_argument("--worker-image", required=True)
    parser.add_argument("--allow-preloaded-tags", action="store_true")
    args = parser.parse_args()
    result = build(args.out, {role: getattr(args, role.replace("-", "_") + "_image")
        for role in ["scheduler", "artifact-store", "worker"]}, args.source_revision,
        allow_preloaded_tags=args.allow_preloaded_tags)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
