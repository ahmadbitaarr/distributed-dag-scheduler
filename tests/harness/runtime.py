"""Launch/kill/collect boundary shared by local, Compose, and course Hokea adapters."""
import json
import os
import signal
import socket
import subprocess
import time
import uuid
from pathlib import Path
from .api import Api, request, wait_for

ROOT = Path(__file__).resolve().parents[2]


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def ready(url):
    try:
        return request(url, "/v1/health")[0] == 200
    except (OSError, TimeoutError):
        return False


class NativeHarness:
    def __init__(self, evidence):
        self.evidence = Path(evidence).resolve()
        self.evidence.mkdir(parents=True, exist_ok=True)
        self.runtime = self.evidence / "runtime"
        self.runtime.mkdir(exist_ok=True)
        self.processes, self.handles = {}, []
        self.scheduler = f"http://127.0.0.1:{free_port()}"
        self.artifacts = f"http://127.0.0.1:{free_port()}"
        self.workers = []

    def launch(self, name, module, env):
        log = open(self.evidence / f"{name}.jsonl", "w")
        self.handles.append(log)
        args = [os.environ.get("JAVA", "java"), "-Xms32m", "-Xmx128m", "-XX:ActiveProcessorCount=1", "-jar",
                str(ROOT / module / "target" / f"{module}-0.2.0.jar")]
        # Affinity restricts each native service to one host CPU. Memory cgroups require Docker.
        if hasattr(os, "sched_getaffinity"):
            cores = sorted(os.sched_getaffinity(0))
            args = ["taskset", "-c", str(cores[len(self.processes) % len(cores)])] + args
        process = subprocess.Popen(args, env={**os.environ, **env}, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        self.processes[name] = process
        return name

    def __enter__(self):
        try:
            self.launch("artifact-store", "artifact-store", {"PORT": self.artifacts.rsplit(":", 1)[1], "DATA_DIR": str(self.runtime / "objects")})
            wait_for(lambda: ready(self.artifacts), description="artifact readiness")
            self.launch("scheduler", "scheduler", {"PORT": self.scheduler.rsplit(":", 1)[1], "ARTIFACT_BASE_URL": self.artifacts})
            wait_for(lambda: ready(self.scheduler), description="scheduler readiness")
            self.api = Api(self.scheduler, self.artifacts)
            return self
        except BaseException:
            self.close()
            raise

    def start_worker(self, env=None):
        name = f"worker-{len(self.workers) + 1}"
        self.launch(name, "worker", {"SCHEDULER_URL": self.scheduler, "ARTIFACT_BASE_URL": self.artifacts, **(env or {})})
        self.workers.append(name)
        wait_for(lambda: any(e["event_type"] == "worker_session_started" for e in self.worker_events(name)), description=f"{name} readiness")
        return name

    def worker_events(self, name):
        result = []
        for line in (self.evidence / f"{name}.jsonl").read_text().splitlines():
            try:
                value = json.loads(line)
                if "event_type" in value:
                    result.append(value)
            except json.JSONDecodeError:
                pass  # Raw logs are retained, including startup diagnostics and in-progress writes.
        return result

    def worker_running(self, name):
        return self.processes[name].poll() is None

    def restart_scheduler(self):
        """Start a new scheduler run on the same address; the old run's state is gone (architecture §8)."""
        process = self.processes["scheduler"]
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=10)
        self.restarts = getattr(self, "restarts", 0) + 1
        name = f"scheduler-run{self.restarts + 1}"
        self.launch(name, "scheduler", {"PORT": self.scheduler.rsplit(":", 1)[1], "ARTIFACT_BASE_URL": self.artifacts})
        self.processes["scheduler"] = self.processes.pop(name)
        wait_for(lambda: ready(self.scheduler), description="restarted scheduler readiness")
        self.api = Api(self.scheduler, self.artifacts)
        return self.api.run_id

    def stop_artifacts(self):
        """Fault hook for the storage-unavailable API test: stop the artifact service, keep the scheduler."""
        process = self.processes["artifact-store"]
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=10)

    def kill_worker(self, name):
        process = self.processes[name]
        os.killpg(process.pid, signal.SIGKILL)
        code = process.wait(timeout=5)
        assert code == -signal.SIGKILL
        return {"worker": name, "pid": process.pid, "signal": "SIGKILL", "exit_code": code}

    def close(self):
        for process in reversed(list(self.processes.values())):
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=5)
        for handle in self.handles:
            handle.close()

    def __exit__(self, *_):
        try:
            if hasattr(self, "api"):
                self.api.export(self.evidence)
        finally:
            self.close()


class ComposeHarness(NativeHarness):
    def __init__(self, evidence):
        super().__init__(evidence)
        self.project = "ms2-" + uuid.uuid4().hex[:10]
        self.worker_containers = {}
        self.compose_env = {**os.environ, "SCHEDULER_PORT": self.scheduler.rsplit(":", 1)[1],
                            "ARTIFACT_PORT": self.artifacts.rsplit(":", 1)[1], "ARTIFACT_DATA_DIR": str(self.runtime / "objects")}

    def compose(self, *args):
        return subprocess.run(["docker", "compose", "-f", str(ROOT / "deploy/compose/compose.yaml"), "-p", self.project, *args],
                              env=self.compose_env, check=True, capture_output=True, text=True)

    def __enter__(self):
        try:
            self.compose("up", "-d", "--wait", "scheduler", "artifact-store")
            self.api = Api(self.scheduler, self.artifacts)
            return self
        except BaseException:
            self.close()
            raise

    def start_worker(self, env=None):
        name = f"worker-{len(self.workers) + 1}"
        options = []
        for key, value in (env or {}).items():
            options += ["-e", f"{key}={value}"]
        result = self.compose("run", "-d", "--no-deps", "--name", self.project + "-" + name, *options, "worker")
        self.worker_containers[name] = result.stdout.strip().splitlines()[-1]
        self.workers.append(name)
        wait_for(lambda: any(e["event_type"] == "worker_session_started" for e in self.worker_events(name)), description="worker readiness")
        return name

    def worker_events(self, name):
        logs = subprocess.run(["docker", "logs", self.worker_containers[name]], check=True, capture_output=True, text=True)
        path = self.evidence / f"{name}.jsonl"
        path.write_text(logs.stdout + logs.stderr)
        return super().worker_events(name)

    def worker_running(self, name):
        result = subprocess.run(["docker", "inspect", "-f", "{{.State.Running}}", self.worker_containers[name]], check=True, capture_output=True, text=True)
        return result.stdout.strip() == "true"

    def stop_artifacts(self):
        self.compose("stop", "artifact-store")

    def kill_worker(self, name):
        subprocess.run(["docker", "kill", "--signal=KILL", self.worker_containers[name]], check=True, capture_output=True)
        result = subprocess.run(["docker", "wait", self.worker_containers[name]], check=True, capture_output=True, text=True, timeout=10)
        assert result.stdout.strip() == "137"
        return {"worker": name, "container": self.worker_containers[name], "signal": "SIGKILL", "exit_code": 137}

    def close(self):
        try:
            for name in self.workers:
                self.worker_events(name)
            (self.evidence / "compose.log").write_text(self.compose("logs", "--no-color").stdout)
        finally:
            self.compose("down", "--remove-orphans")


def harness(evidence, backend=None):
    backend = backend or os.environ.get("MS2_BACKEND", "native")
    if backend == "native":
        return NativeHarness(evidence)
    if backend == "compose":
        return ComposeHarness(evidence)
    if backend == "hokea":
        from .hokea_adapter import HokeaHarness
        return HokeaHarness(evidence)
    raise ValueError(f"Unknown backend {backend}")
