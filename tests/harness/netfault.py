"""Fault-injecting HTTP proxy for one worker-to-scheduler link (native backend).

A worker started with ``proxy=True`` talks to the scheduler only through its own FaultProxy,
so each fault applies to exactly one link. Tests add rules while the system runs:

    drop_request   the scheduler never sees the request (connection closed, no reply)
    drop_response  the scheduler processes the request, the reply is lost
    delay          wait ``delay_ms`` (uniformly random up to it if ``jitter``) before forwarding
    duplicate      deliver the request twice; the worker receives the second reply

``partition()`` drops every request until ``heal()``. Every exchange is appended to
``proxy-<worker>.jsonl`` in the evidence directory with the action taken, so a reader can
see exactly which messages were lost, delayed or repeated.
"""
import http.client
import http.server
import json
import random
import threading
import time
import urllib.parse

HOP_BY_HOP = {"connection", "keep-alive", "transfer-encoding", "content-length", "date", "server"}


class Rule:
    def __init__(self, action, path=None, times=None, delay_ms=0, jitter=False, probability=1.0,
                 status=None, when=None):
        assert action in ("drop_request", "drop_response", "delay", "duplicate"), action
        self.action, self.path, self.times, self.delay_ms = action, path, times, delay_ms
        self.jitter, self.probability, self.status, self.when = jitter, probability, status, when
        self.applied = 0

    def describe(self):
        return {"action": self.action, "path": self.path, "times": self.times, "delay_ms": self.delay_ms,
                "probability": self.probability, "status": self.status}


class FaultProxy:
    def __init__(self, target, log_path, seed=0):
        self.target = urllib.parse.urlparse(target)
        self.rules, self.lock, self.random = [], threading.Lock(), random.Random(seed)
        self.log = open(log_path, "w")
        self.sequence = 0
        self.partitioned = False
        proxy = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def handle_one(self):
                body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
                proxy.exchange(self, body)

            do_GET = do_POST = handle_one

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    # ---- control, from the test thread ----

    def add(self, action, **options):
        rule = Rule(action, **options)
        with self.lock:
            self.rules.append(rule)
        return rule

    def remove(self, rule):
        with self.lock:
            self.rules.remove(rule)

    def clear(self):
        with self.lock:
            self.rules.clear()
            self.partitioned = False

    def partition(self):
        with self.lock:
            self.partitioned = True
        self.record({"control": "partition"})

    def heal(self):
        with self.lock:
            self.partitioned = False
        self.record({"control": "heal"})

    def applied(self, action, path=None):
        return [r for r in self.records() if r.get("action") == action and (path is None or r.get("path") == path)]

    def records(self):
        with self.lock:
            self.log.flush()
        with open(self.log.name) as stream:
            return [json.loads(line) for line in stream if line.strip()]

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        with self.lock:
            self.log.close()

    # ---- data path ----

    def record(self, entry):
        with self.lock:
            self.sequence += 1
            self.log.write(json.dumps({"proxy_seq": self.sequence, "monotonic_ns": time.monotonic_ns(), **entry}) + "\n")
            self.log.flush()

    def choose(self, phase, path, body, status=None):
        """Pick matching rules for a phase ('request' or 'response'); consume their budgets."""
        chosen = []
        with self.lock:
            for rule in self.rules:
                wanted = phase == ("response" if rule.action == "drop_response" else "request")
                if not wanted or (rule.path is not None and rule.path != path):
                    continue
                if rule.status is not None and rule.status != status:
                    continue
                if rule.when is not None and not rule.when(body):
                    continue
                if rule.times is not None and rule.applied >= rule.times:
                    continue
                if rule.probability < 1.0 and self.random.random() >= rule.probability:
                    continue
                rule.applied += 1
                chosen.append(rule)
        return chosen

    def forward(self, handler, body):
        conn = http.client.HTTPConnection(self.target.hostname, self.target.port, timeout=10)
        try:
            headers = {"Content-Type": "application/json"} if body else {}
            conn.request(handler.command, handler.path, body or None, headers)
            response = conn.getresponse()
            return response.status, response.getheaders(), response.read()
        finally:
            conn.close()

    def exchange(self, handler, raw):
        path = urllib.parse.urlparse(handler.path).path
        try:
            body = json.loads(raw) if raw else None
        except ValueError:
            body = None
        entry = {"method": handler.command, "path": path, "request": body}
        if self.partitioned:
            self.record({**entry, "action": "drop_request", "rule": "partition"})
            handler.close_connection = True
            return
        rules = self.choose("request", path, body)
        for rule in rules:
            if rule.action == "drop_request":
                self.record({**entry, "action": "drop_request", "rule": rule.describe()})
                handler.close_connection = True
                return
        delay = sum((self.random.uniform(0, r.delay_ms) if r.jitter else r.delay_ms) for r in rules if r.action == "delay")
        if delay:
            time.sleep(delay / 1000)
        try:
            status, headers, payload = self.forward(handler, raw)
            duplicated = any(r.action == "duplicate" for r in rules)
            first = None
            if duplicated:
                first = {"status": status, "response": payload.decode(errors="replace")[:2000]}
                status, headers, payload = self.forward(handler, raw)
        except OSError as error:
            self.record({**entry, "action": "upstream_error", "error": str(error)})
            handler.close_connection = True
            return
        response_text = payload.decode(errors="replace")[:2000]
        after = self.choose("response", path, body, status)
        if after:
            self.record({**entry, "action": "drop_response", "status": status, "response": response_text,
                         "rule": after[0].describe()})
            handler.close_connection = True
            return
        action = "duplicate" if duplicated else ("delay" if delay else "forward")
        self.record({**entry, "action": action, "status": status, "response": response_text,
                     **({"delay_ms": round(delay, 1)} if delay else {}), **({"first_delivery": first} if first else {})})
        handler.send_response(status)
        for key, value in headers:
            if key.lower() not in HOP_BY_HOP:
                handler.send_header(key, value)
        handler.send_header("Content-Length", str(len(payload)))
        handler.end_headers()
        handler.wfile.write(payload)
