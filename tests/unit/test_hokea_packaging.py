import base64
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("package_runner", ROOT / "deploy/hokea/package_runner.py")
packaging = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packaging)
IMAGES = {role: "registry.example/" + role + "@sha256:" + "a" * 64
          for role in ["scheduler", "artifact-store", "worker"]}


def test_roundtrip_imports_exact_oracles_and_preserves_nested_files(tmp_path):
    output = tmp_path / "runner"
    report = packaging.build(output, IMAGES, "step11-source-id")
    assert report["bytes"] < report["budget"] == 900_000
    assert sorted(p.name for p in output.iterdir()) == report["files"]
    payload = json.loads((output / "payload.json").read_text())
    for name, item in payload["files"].items():
        assert base64.b64decode(item["base64"]) == (ROOT / name).read_bytes()
    # Collection imports original functions and strict xfail metadata, without any runtime.
    result = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q"],
                            cwd=output, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "3 tests collected" in result.stdout
    assert (output / "_project/tests/faults/test_worker_crash.py").read_bytes() == (ROOT / "tests/faults/test_worker_crash.py").read_bytes()
    assert payload["environment"]["MS2_REQUIRE_XFAIL"] == "1"
    assert payload["environment"]["MS2_HOKEA_RUNTIME"] == "kubernetes"


def test_rejects_mutable_images_unless_staff_preloaded_is_explicit(tmp_path):
    tags = {role: role + ":0.2.0" for role in IMAGES}
    with pytest.raises(ValueError, match="immutable"):
        packaging.build(tmp_path / "reject", tags, "source")
    assert not (tmp_path / "reject").exists()
    assert packaging.build(tmp_path / "allow", tags, "source", allow_preloaded_tags=True)["bytes"] < 900_000


def test_budget_failure_and_existing_directory_never_overwrite(tmp_path, monkeypatch):
    monkeypatch.setattr(packaging, "BUDGET", 10)
    with pytest.raises(ValueError, match="budget"):
        packaging.build(tmp_path / "too-big", IMAGES, "source")
    assert not (tmp_path / "too-big").exists()
    monkeypatch.setattr(packaging, "BUDGET", 900_000)
    output = tmp_path / "existing"
    packaging.build(output, IMAGES, "source")
    original = (output / "payload.json").read_bytes()
    with pytest.raises(FileExistsError):
        packaging.build(output, IMAGES, "changed-source")
    assert (output / "payload.json").read_bytes() == original


def test_bootstrap_rejects_corrupted_file_and_traversal(tmp_path):
    output = tmp_path / "runner"
    packaging.build(output, IMAGES, "source")
    path = output / "payload.json"
    payload = json.loads(path.read_text())
    payload["files"]["tests/__init__.py"]["sha256"] = "bad"
    path.write_text(json.dumps(payload))
    result = subprocess.run([sys.executable, "conftest.py"], cwd=output, capture_output=True, text=True)
    assert result.returncode != 0 and "checksum mismatch" in result.stderr
    payload["files"] = {"../escape": next(iter(payload["files"].values()))}
    path.write_text(json.dumps(payload))
    result = subprocess.run([sys.executable, "conftest.py"], cwd=output, capture_output=True, text=True)
    assert result.returncode != 0 and "Unsafe payload path" in result.stderr
    assert not (tmp_path / "escape").exists()
