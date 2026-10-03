"""Pinned Hokea orchestration only; the existing Api and correctness tests own semantics."""
import hashlib
import importlib
import json
import os
import re
import shutil
import subprocess
import uuid
from pathlib import Path

from .api import Api, wait_for
from .runtime import ROOT, ready

HOKEA_SHA = "427b94634b1736ba8e59d4977836162aa58bd2cb"
PIN = ROOT / "deploy/hokea/HOKEA_API_SHA256.json"


def verify_package(package):
    pin = json.loads(PIN.read_text())
    if pin["revision"] != HOKEA_SHA:
        raise RuntimeError("Hokea pin document disagrees with adapter revision")
    directory = Path(package)
    for name, expected in pin["package_files"].items():
        path = directory / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise RuntimeError(f"Hokea source mismatch at {name}; require {HOKEA_SHA}")
    return HOKEA_SHA


def docker_config(config, shared_network, worker):
    """Narrow pinned _compose_config bridge: existing images, shared HTTP network, no worker port."""
    for service in config["services"].values():
        service["restart"] = "no"
        service.pop("cap_add", None)  # This experiment uses process faults only.
        if worker:
            service.pop("ports", None)
        if shared_network:
            service["networks"]["ms2-services"] = {"priority": 200}
    if shared_network:
        config["networks"]["ms2-services"] = {"external": True, "name": shared_network}
    return config


def worker_pod(manifest):
    manifest["spec"]["containers"][0].pop("ports", None)
    return manifest


class Factory:
    """Import only when the Hokea backend is selected. No credential discovery."""
    def __init__(self, mode, namespace):
        if os.environ.get("HOKEA_TAKEOVER"):
            raise ValueError("HOKEA_TAKEOVER must be unset; this adapter never takes over existing resources")
        module = importlib.import_module("hokea.cluster")
        verify_package(Path(module.__file__).parent)
        self.mode, self.namespace = mode, namespace
        if mode == "docker":
            parent = module.Cluster
            class ServiceCluster(parent):
                def _compose_config(self):
                    return docker_config(super()._compose_config(), self.ms2_shared, self.ms2_worker)
            self.cluster_type = ServiceCluster
        else:
            parent = importlib.import_module("hokea.kube").KubeCluster
            class ServiceCluster(parent):
                def _pod_manifest(self, i):
                    pod = super()._pod_manifest(i)
                    return worker_pod(pod) if self.ms2_worker else pod
                def _peers_service_manifest(self):
                    service = super()._peers_service_manifest()
                    if self.ms2_worker:
                        service["spec"].pop("ports", None)
                    return service
            self.cluster_type = ServiceCluster

    def create(self, *, role, image, name, port, env, workdir, shared_network):
        options = dict(nodes=1, name=name, port=port, env=env, cpus=1.0,
                       workdir=workdir, up_timeout=120)
        if self.mode == "docker":
            # Public Dockerfile mode inherits the existing image ENTRYPOINT; no source bind mount.
            workdir.mkdir(parents=True, exist_ok=True)
            (workdir / "Dockerfile").write_text(f"FROM {image}\n")
            options.update(dockerfile=workdir, memory="512m")
        else:
            options.update(image=image, namespace=self.namespace, memory="512Mi",
                           expose="internal" if role == "worker" else os.environ.get("MS2_HOKEA_EXPOSE", "internal"),
                           takeover=False)
        cluster = self.cluster_type(**options)
        cluster.ms2_shared, cluster.ms2_worker = shared_network, role == "worker"
        return cluster

    def observe(self, cluster):
        node = cluster.node(1)
        if self.mode == "docker":
            result = subprocess.run(["docker", "inspect", node.name], check=True, capture_output=True, text=True)
            obj = json.loads(result.stdout)[0]
            return {"instance_id": obj["Id"], "running": obj["State"]["Running"],
                    "exit_code": obj["State"]["ExitCode"], "restart_count": obj["RestartCount"],
                    "restart_policy": obj["HostConfig"]["RestartPolicy"]["Name"], "image_id": obj["Image"]}
        # Unlike KubeNode.status(), API/credential errors must not masquerade as "gone".
        result = cluster._kubectl("get", "pod", node.name, "-o", "json", "--ignore-not-found")
        if not result.stdout.strip():
            return {"instance_id": None, "running": False, "gone": True}
        obj = json.loads(result.stdout)
        status = obj.get("status", {})
        containers = status.get("containerStatuses", [])
        running = status.get("phase") == "Running" and bool(containers) and all(
            "running" in c.get("state", {}) for c in containers)
        return {"instance_id": obj["metadata"]["uid"], "running": running,
                "gone": False, "restart_policy": obj["spec"]["restartPolicy"],
                "container_statuses": containers}

    def release(self, cluster):
        # Hokea down() removes containers/networks, but retains its generated image tag.
        # Remove only this run's wrapper tag, never base images or global build caches.
        if self.mode == "docker" and hasattr(cluster, "_image_tag"):
            subprocess.run(["docker", "image", "rm", cluster._image_tag], check=True, capture_output=True, text=True)


class HokeaHarness:
    def __init__(self, evidence, *, factory=None, mode=None, namespace=None):
        self.evidence = Path(evidence).resolve()
        self.evidence.mkdir(parents=True, exist_ok=True)
        self.runtime = self.evidence / "runtime/hokea"
        self.runtime.mkdir(parents=True, exist_ok=True)
        self.orchestration = self.evidence / "hokea"
        self.orchestration.mkdir(exist_ok=True)
        self.mode = mode or os.environ.get("MS2_HOKEA_RUNTIME", "docker")
        if self.mode not in {"docker", "kubernetes"}:
            raise ValueError("MS2_HOKEA_RUNTIME must be docker or kubernetes")
        self.namespace = namespace or os.environ.get("HOKEA_NAMESPACE")
        if self.mode == "kubernetes" and not self.namespace:
            raise ValueError("Explicit HOKEA_NAMESPACE required for Kubernetes")
        self.images = {role: os.environ.get("MS2_HOKEA_" + role.upper().replace("-", "_") + "_IMAGE", f"dag-ms2/{role}:0.2.0")
                       for role in ["scheduler", "artifact-store", "worker"]}
        for image in self.images.values():
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9./_:@-]*", image):
                raise ValueError("Image must be an OCI reference without whitespace or Dockerfile instructions")
        self.factory = factory or Factory(self.mode, self.namespace)
        self.prefix = "ms2-" + uuid.uuid4().hex[:10]
        self.clusters, self.workers, self.identities, self.killed = {}, [], {}, {}
        self.shared_network = None
        self.cleanup = False
        self.records = []

    def _write(self):
        (self.orchestration / "metadata.json").write_text(json.dumps({
            "hokea_revision": HOKEA_SHA, "runtime": self.mode, "namespace": self.namespace,
            "source_revision": os.environ.get("MS2_SOURCE_REV"), "images": self.images,
            "records": self.records, "cleanup_succeeded": self.cleanup}, indent=2))

    def _launch(self, name, role, env, port):
        cluster = self.factory.create(role=role, image=self.images[role], name=self.prefix + "-" + name,
                                      port=port, env=env, workdir=self.runtime / name,
                                      shared_network=self.shared_network)
        self.clusters[name] = cluster  # register before up so partial startup is cleaned.
        cluster.up()  # Deliberately bypass hokea pytest's blanket wait_healthy(/health).
        observation = wait_for(lambda: (state if (state := self.factory.observe(cluster))["running"] else None),
                               timeout=120, description=f"Hokea {name} process startup")
        assert observation.get("restart_policy") in {"no", "", "Never"}, observation
        self.identities[name] = observation["instance_id"]
        self.records.append({"role": role, "name": name, "node": cluster.node(1).name,
                             "node_index": 1, "env": env, "observed": observation})
        self._write()
        return cluster

    def _internal_url(self, cluster, port):
        if self.mode == "docker":
            return f"http://{cluster.node(1).name}:{port}"
        return f"http://node-1.{cluster.prefix}-peers.{self.namespace}.svc.cluster.local:{port}"

    def __enter__(self):
        try:
            store = self._launch("artifact-store", "artifact-store", {"PORT": "8081", "DATA_DIR": "/data"}, 8081)
            self.artifacts = store.node(1).url
            if self.mode == "docker":
                self.shared_network = store.prefix + "-client"
            self.artifact_internal = self._internal_url(store, 8081)
            wait_for(lambda: ready(self.artifacts), timeout=90, description="Hokea artifact readiness")
            scheduler = self._launch("scheduler", "scheduler", {"PORT": "8080", "ARTIFACT_BASE_URL": self.artifact_internal}, 8080)
            self.scheduler = scheduler.node(1).url
            self.scheduler_internal = self._internal_url(scheduler, 8080)
            wait_for(lambda: ready(self.scheduler), timeout=90, description="Hokea scheduler readiness")
            self.api = Api(self.scheduler, self.artifacts)
            return self
        except BaseException:
            self.close()
            raise

    def start_worker(self, env=None):
        name = f"worker-{len(self.workers) + 1}"
        self.workers.append(name)
        self._launch(name, "worker", {"SCHEDULER_URL": self.scheduler_internal,
                    "ARTIFACT_BASE_URL": self.artifact_internal, "POLL_INTERVAL_MS": "100",
                    "OPERATION_TIMEOUT_MS": "30000", "ENABLE_TEST_HOOKS": "false", **(env or {})}, 1)
        wait_for(lambda: self.worker_running(name) and any(e["event_type"] == "worker_session_started"
                    for e in self.worker_events(name)), timeout=90, description="Hokea worker session readiness")
        return name

    def _logs(self, name):
        path = self.evidence / f"{name}.jsonl"
        if name not in self.killed:
            path.write_text(self.clusters[name].node(1).logs(tail=-1))
        return path.read_text() if path.exists() else ""

    def worker_events(self, name):
        events = []
        for line in self._logs(name).splitlines():
            try:
                obj = json.loads(line)
                if isinstance(obj, dict) and "event_type" in obj:
                    events.append(obj)
            except json.JSONDecodeError:
                pass  # raw stdout including diagnostics is retained.
        return events

    def worker_running(self, name):
        state = self.factory.observe(self.clusters[name])
        if name in self.killed:
            # Detect recreation even when a new pod is Pending, not yet Running.
            assert state.get("instance_id") in {None, self.identities[name]}, "Killed worker was recreated"
            assert not state["running"], "Killed worker resumed"
            return False
        assert state["instance_id"] == self.identities[name], "Worker instance changed"
        return state["running"]

    def kill_worker(self, name):
        if name not in self.workers or name in self.killed:
            raise ValueError("Kill must target one live known worker")
        cluster = self.clusters[name]
        assert self.worker_running(name), "Target worker is not running"
        events = self.worker_events(name)  # seal pre-delete logs (Kubernetes deletes its log address).
        sessions = {e["worker_session_id"] for e in events if e["event_type"] == "worker_session_started"}
        assert len(sessions) == 1
        cluster.kill(1)
        wait_for(lambda: not self.factory.observe(cluster)["running"], timeout=15, description="Hokea hard death")
        after = self.factory.observe(cluster)
        if self.mode == "docker":
            assert after["instance_id"] == self.identities[name] and after["exit_code"] == 137
            assert after["restart_count"] == 0, "Target worker had restarted"
        else:
            assert after["gone"] and after["instance_id"] is None
        evidence = {"worker": name, "hokea_revision": HOKEA_SHA, "runtime": self.mode,
                    "node": cluster.node(1).name, "node_index": 1, "old_instance_id": self.identities[name],
                    "worker_session_id": sessions.pop(), "hard_kill_requested": True, "kill_completed": True,
                    "old_instance_running": False, "automatic_restart_observed": False,
                    "mechanism": "docker_sigkill" if self.mode == "docker" else "force_pod_deletion",
                    "death_observation": after}
        if self.mode == "docker":
            evidence.update(signal="SIGKILL", exit_code=137)
        # A deleted Kubernetes Pod is evidence about the API object. No kubelet/process-death
        # guarantee is claimed if the node itself is partitioned from the control plane.
        self.killed[name] = evidence
        self.records.append({"hard_kill": evidence})
        self._write()
        assert not self.worker_running(name)
        return dict(evidence)

    def stop_artifacts(self):
        self._logs("artifact-store")
        self.clusters["artifact-store"].stop(1)
        self.killed["artifact-store"] = {"mechanism": "stop"}

    def close(self):
        errors = []
        for name, cluster in reversed(list(self.clusters.items())):
            try:
                self._logs(name)
                # Supplemental original Hokea fault timeline and ambient raw capture.
                dest = self.orchestration / name
                dest.mkdir(exist_ok=True)
                (dest / "faults.jsonl").write_text("".join(json.dumps(x) + "\n" for x in cluster.fault_log.events))
            except BaseException as error:
                errors.append(error)
            finally:
                try:
                    cluster.down()
                    self.factory.release(cluster)
                except BaseException as error:
                    errors.append(error)
                # down() stops/flushes the ambient collector before copying its files.
                try:
                    captures = cluster.workdir / "events"
                    if captures.exists():
                        shutil.copytree(captures, self.orchestration / name / "events", dirs_exist_ok=True)
                except BaseException as error:
                    errors.append(error)
        self.cleanup = not errors
        self._write()
        if errors:
            raise RuntimeError("Hokea log collection/cleanup failed: " + "; ".join(str(e) for e in errors)) from errors[0]

    def __exit__(self, *_):
        try:
            if hasattr(self, "api"):
                self.api.export(self.evidence)
        finally:
            self.close()
