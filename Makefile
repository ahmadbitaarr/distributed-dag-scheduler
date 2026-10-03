# MS2 evaluator commands (architecture §15). Run from the repository root.
COMPOSE = docker compose -f deploy/compose/compose.yaml
WORKERS ?= 3
PYTHON ?= python3

.PHONY: build up demo test fault-demo bench down

build:            ## compile and run the JUnit tests
	mvn -B verify

up:               ## build images, start scheduler + artifact store + $(WORKERS) workers, wait for readiness
	$(COMPOSE) up -d --build --wait --scale worker=$(WORKERS) scheduler artifact-store worker

demo:             ## run the functional and video demos against `make up`; outputs in results/demo/
	$(PYTHON) -m tests.harness.demo

test:             ## JUnit + full pytest suite in the Linux harness container; requires exactly one XFAIL
	sh deploy/harness/run.sh

fault-demo:       ## same recovery oracle as make test; intentional nonzero RecoveryNotObserved in MS2
	sh deploy/harness/run.sh sh -c 'mvn -B -q package -DskipTests && pytest -q --runxfail tests/faults/test_worker_crash.py'

bench:            ## full C x W x 5 matrix on capped Compose services; raw + summary in results/benchmark/<UTC time>/
	$(COMPOSE) build
	$(PYTHON) -m benchmarks.run --backend compose --out results/benchmark/$$(date -u +%Y%m%dT%H%M%SZ)

down:             ## stop the deployment; artifact files and results/ are kept
	$(COMPOSE) down
