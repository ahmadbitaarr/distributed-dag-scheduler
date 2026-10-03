"""Unpack exact project bytes inside Hokea's writable /project."""
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
