"""Orchestration contract tests. Fakes never contact Docker or Kubernetes."""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.harness import hokea_adapter as adapter


class FakeNode:
    def __init__(self, cluster):
        self.cluster, self.name = cluster, cluster.prefix + "-node1"
        self.url = "http://host:" + str(cluster.options["port"])
    def logs(self, tail):
        assert tail == -1
        if self.cluster.deleted:
            raise RuntimeError("deleted Pod log address")
        if self.cluster.options["role"] == "worker":
            return "diagnostic\n" + json.dumps({"event_type": "worker_session_started",
                "worker_session_id": self.name + "-session"}) + "\n"
        return json.dumps({"event_type": "service_ready"}) + "\n"


class FakeCluster:
    def __init__(self, options, factory):
        self.options, self.factory = options, factory
        self.prefix, self.workdir = "hokea-" + options["name"], options["workdir"]
        self.fault_log = SimpleNamespace(events=[])
        self.running, self.deleted, self.exit_code = False, False, 0
        self.id = self.prefix + "-instance"
        self.down_called = False
    def node(self, index):
        assert index == 1
        return FakeNode(self)
    def up(self):
        self.workdir.mkdir(parents=True, exist_ok=True)
        if self.factory.fail_up == self.options["role"]:
            raise RuntimeError("startup failed")
        self.running = True
    def kill(self, index):
        assert index == 1
        self.fault_log.events.append({"event": "kill", "node": index})
        self.running, self.exit_code = False, 137
        self.deleted = self.factory.mode == "kubernetes"
    def stop(self, index):
        self.running = False
    def down(self):
        self.down_called = True
        self.factory.down_order.append(self.options["role"])
        captures = self.workdir / "events"
        captures.mkdir(parents=True, exist_ok=True)
        (captures / "node1.raw").write_text("collector flushed\n")
        self.running = False
        if self.factory.fail_down == self.options["role"]:
            raise RuntimeError("cleanup failed")


class FakeFactory:
    def __init__(self, mode="docker"):
        self.mode, self.created, self.down_order = mode, [], []
        self.fail_up = self.fail_down = None
        self.observe_error = None
    def create(self, **options):
        cluster = FakeCluster(options, self)
        self.created.append(cluster)
        return cluster
    def observe(self, cluster):
        if self.observe_error:
            raise self.observe_error
        return {"instance_id": None if cluster.deleted else cluster.id,
                "running": cluster.running, "exit_code": cluster.exit_code,
                "restart_count": 0, "gone": cluster.deleted,
                "restart_policy": "Never" if self.mode == "kubernetes" else "no"}
    def release(self, cluster):
        assert cluster.down_called


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    monkeypatch.setattr(adapter, "ready", lambda url: True)
    class Api:
        def __init__(self, scheduler, artifacts):
            self.scheduler, self.artifacts = scheduler, artifacts
        def export(self, evidence):
            (evidence / "exported").touch()
    monkeypatch.setattr(adapter, "Api", Api)
    def make(mode="docker"):
        factory = FakeFactory(mode)
        return adapter.HokeaHarness(tmp_path, factory=factory, mode=mode, namespace="team-test"), factory
    return make


@pytest.mark.parametrize("mode", ["docker", "kubernetes"])
def test_service_parameters_addresses_and_private_worker_env(prepared, mode):
    h, factory = prepared(mode)
    with h:
        store, scheduler = factory.created
        assert store.options["image"] == "dag-ms2/artifact-store:0.2.0"
        assert store.options["env"] == {"PORT": "8081", "DATA_DIR": "/data"}
        assert scheduler.options["port"] == 8080
        assert scheduler.options["env"]["ARTIFACT_BASE_URL"] == h.artifact_internal
        a = h.start_worker({"ENABLE_TEST_HOOKS": "true", "TEST_GATE_TASK": "X", "OPERATION_TIMEOUT_MS": "120000"})
        b = h.start_worker()
        assert (a, b) == ("worker-1", "worker-2")
        first, second = factory.created[-2:]
        assert first.options["env"]["TEST_GATE_TASK"] == "X"
        assert second.options["env"]["ENABLE_TEST_HOOKS"] == "false"
        assert "TEST_GATE_TASK" not in second.options["env"]
        assert second.options["env"]["OPERATION_TIMEOUT_MS"] == "30000"
        assert second.options["env"]["SCHEDULER_URL"] == h.scheduler_internal
        assert len({c.options["name"] for c in factory.created}) == 4
        assert len({c.workdir for c in factory.created}) == 4
        if mode == "docker":
            assert scheduler.options["shared_network"] == store.prefix + "-client"
            assert store.node(1).name in h.artifact_internal
        else:
            assert h.artifact_internal.endswith(".team-test.svc.cluster.local:8081")
    assert h.cleanup and (h.evidence / "exported").exists()
    assert factory.down_order == ["worker", "worker", "scheduler", "artifact-store"]


@pytest.mark.parametrize("mode", ["docker", "kubernetes"])
def test_hard_kill_target_death_evidence_and_cached_logs(prepared, mode):
    h, factory = prepared(mode)
    with h:
        a, b = h.start_worker(), h.start_worker()
        original = h.worker_events(a)
        result = h.kill_worker(a)
        assert result["worker"] == a and result["node_index"] == 1
        assert result["old_instance_id"] == h.identities[a]
        assert result["kill_completed"] and result["hard_kill_requested"]
        assert not result["old_instance_running"] and not result["automatic_restart_observed"]
        assert not h.worker_running(a) and h.worker_running(b)
        assert h.worker_events(a) == original
        if mode == "docker":
            assert result["exit_code"] == 137 and result["signal"] == "SIGKILL"
        else:
            assert result["death_observation"]["gone"]
            assert "exit_code" not in result and "signal" not in result
        with pytest.raises(ValueError):
            h.kill_worker(a)
        with pytest.raises(ValueError):
            h.kill_worker("scheduler")
    assert (h.orchestration / a / "faults.jsonl").read_text()
    assert (h.orchestration / b / "events/node1.raw").read_text() == "collector flushed\n"


def test_pending_recreation_cannot_be_mistaken_for_dead(prepared):
    h, factory = prepared("kubernetes")
    with h:
        a = h.start_worker()
        h.kill_worker(a)
        h.clusters[a].deleted = False
        h.clusters[a].id = "replacement-uid"
        with pytest.raises(AssertionError, match="recreated"):
            h.worker_running(a)


def test_observation_error_is_not_worker_death(prepared):
    h, factory = prepared()
    with h:
        a = h.start_worker()
        factory.observe_error = RuntimeError("API access denied")
        with pytest.raises(RuntimeError, match="API access denied"):
            h.worker_running(a)
        factory.observe_error = None


def test_partial_startup_is_cleaned_and_fails(prepared):
    h, factory = prepared()
    factory.fail_up = "scheduler"
    with pytest.raises(RuntimeError, match="startup failed"):
        h.__enter__()
    assert all(c.down_called for c in factory.created)
    assert factory.down_order == ["scheduler", "artifact-store"]


def test_cleanup_failure_is_visible_and_does_not_skip_other_resources(prepared):
    h, factory = prepared()
    h.__enter__()
    h.start_worker()
    factory.fail_down = "worker"
    with pytest.raises(RuntimeError, match="cleanup failed"):
        h.__exit__(None, None, None)
    assert all(c.down_called for c in factory.created) and not h.cleanup
    assert not json.loads((h.orchestration / "metadata.json").read_text())["cleanup_succeeded"]


def test_export_failure_still_cleans_resources(prepared):
    h, factory = prepared()
    h.__enter__()
    h.api.export = lambda path: (_ for _ in ()).throw(RuntimeError("export failed"))
    with pytest.raises(RuntimeError, match="export failed"):
        h.__exit__(None, None, None)
    assert h.cleanup and all(c.down_called for c in factory.created)


def test_no_worker_ports_restart_or_shared_storage_in_docker_bridge():
    config = {"services": {"node1": {"ports": ["1234:1"], "cap_add": ["NET_ADMIN"],
              "tmpfs": ["/data"], "networks": {"client": {"priority": 100}}}}, "networks": {"client": {}}}
    result = adapter.docker_config(config, "store-client", True)
    node = result["services"]["node1"]
    assert "ports" not in node and "volumes" not in node and "cap_add" not in node
    assert node["tmpfs"] == ["/data"] and node["restart"] == "no"
    assert result["networks"]["ms2-services"] == {"external": True, "name": "store-client"}


def test_worker_manifest_removes_port_without_adding_server_or_storage():
    pod = {"spec": {"restartPolicy": "Never", "containers": [{"image": "worker", "ports": [{"containerPort": 1}]}],
                    "volumes": [{"name": "data", "emptyDir": {}}]}}
    assert adapter.worker_pod(pod)["spec"]["containers"] == [{"image": "worker"}]
    assert pod["spec"]["restartPolicy"] == "Never"
    assert pod["spec"]["volumes"] == [{"name": "data", "emptyDir": {}}]


def test_exact_package_pin_rejects_modified_source(tmp_path, monkeypatch):
    package = tmp_path / "hokea"
    package.mkdir()
    (package / "cluster.py").write_text("pinned\n")
    pin = tmp_path / "pin.json"
    pin.write_text(json.dumps({"revision": adapter.HOKEA_SHA,
        "package_files": {"cluster.py": hashlib.sha256(b"pinned\n").hexdigest()}}))
    monkeypatch.setattr(adapter, "PIN", pin)
    assert adapter.verify_package(package) == adapter.HOKEA_SHA
    (package / "cluster.py").write_text("upgrade\n")
    with pytest.raises(RuntimeError, match="source mismatch"):
        adapter.verify_package(package)


def test_factory_constructor_parameters_and_no_source_bind_mount(tmp_path):
    class Constructor:
        def __init__(self, **kw):
            self.kw = kw
    factory = adapter.Factory.__new__(adapter.Factory)
    factory.mode, factory.namespace, factory.cluster_type = "docker", "team-test", Constructor
    cluster = factory.create(role="worker", image="registry/worker@sha256:" + "a" * 64,
        name="ms2-example-worker-1", port=1, env={"ENABLE_TEST_HOOKS": "false"},
        workdir=tmp_path / "worker", shared_network="store-client")
    assert cluster.kw["nodes"] == 1 and cluster.kw["cpus"] == 1.0 and cluster.kw["memory"] == "512m"
    assert "src" not in cluster.kw and "cmd" not in cluster.kw and "data" not in cluster.kw
    assert (cluster.kw["dockerfile"] / "Dockerfile").read_text().startswith("FROM registry/worker@sha256:")
    factory.mode = "kubernetes"
    cluster = factory.create(role="worker", image="worker", name="ms2-example-worker-1", port=1,
        env={}, workdir=tmp_path / "kube", shared_network=None)
    assert cluster.kw["image"] == "worker" and cluster.kw["expose"] == "internal"
    assert cluster.kw["takeover"] is False and cluster.kw["memory"] == "512Mi"
    assert "dockerfile" not in cluster.kw


def test_strict_kubernetes_observation_propagates_command_failure():
    factory = adapter.Factory.__new__(adapter.Factory)
    factory.mode = "kubernetes"
    class Cluster:
        def node(self, i):
            return SimpleNamespace(name="target")
        def _kubectl(self, *args):
            assert "--ignore-not-found" in args
            raise RuntimeError("kubectl failed")
    with pytest.raises(RuntimeError, match="kubectl failed"):
        factory.observe(Cluster())


def test_takeover_and_missing_namespace_are_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("HOKEA_TAKEOVER", "1")
    with pytest.raises(ValueError, match="TAKEOVER"):
        adapter.Factory("kubernetes", "team-test")
    monkeypatch.delenv("HOKEA_NAMESPACE", raising=False)
    with pytest.raises(ValueError, match="HOKEA_NAMESPACE"):
        adapter.HokeaHarness(tmp_path, factory=FakeFactory(), mode="kubernetes")


def test_running_pod_with_terminated_container_is_not_alive():
    factory = adapter.Factory.__new__(adapter.Factory)
    factory.mode = "kubernetes"
    pod = {"metadata": {"uid": "original"}, "spec": {"restartPolicy": "Never"},
           "status": {"phase": "Running", "containerStatuses": [{"state": {"terminated": {"exitCode": 1}}}]}}
    cluster = SimpleNamespace(node=lambda i: SimpleNamespace(name="target"),
                              _kubectl=lambda *args: SimpleNamespace(stdout=json.dumps(pod)))
    assert not factory.observe(cluster)["running"]
    pod["status"]["containerStatuses"][0]["state"] = {"running": {"startedAt": "now"}}
    assert factory.observe(cluster)["running"]


def test_only_owned_wrapper_tag_is_released(monkeypatch):
    factory = adapter.Factory.__new__(adapter.Factory)
    factory.mode = "docker"
    calls = []
    monkeypatch.setattr(adapter.subprocess, "run", lambda args, **kwargs: calls.append((args, kwargs)))
    factory.release(SimpleNamespace(_image_tag="hokea-ms2-owned-img"))
    assert calls == [(["docker", "image", "rm", "hokea-ms2-owned-img"],
                     {"check": True, "capture_output": True, "text": True})]
    factory.mode = "kubernetes"
    factory.release(SimpleNamespace())
    assert len(calls) == 1
