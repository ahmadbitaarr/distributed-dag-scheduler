# Evaluator commands (architecture §15). Run from the repository root; Docker is the only host requirement.
COMPOSE = docker compose -f deploy/compose/compose.yaml
WORKERS ?= 3
PYTHON ?= python3

.PHONY: build up demo test faults fault-demo bench bench-recovery down

build:            ## compile and run the JUnit tests
	mvn -B verify

up:               ## build images, start scheduler + artifact store + $(WORKERS) workers, wait for readiness
	$(COMPOSE) up -d --build --wait --scale worker=$(WORKERS) scheduler artifact-store worker

demo:             ## run the functional and video demos against `make up`; outputs in results/demo/
	$(PYTHON) -m tests.harness.demo

test:             ## THE single command: JUnit + every pytest suite (unit, integration, faults) in the Linux harness container; zero XFAILs allowed
	sh deploy/harness/run.sh

faults:           ## only the fault-injection suites (crash/restart/pause/loss/delay/duplication/partition/chaos)
	sh deploy/harness/run.sh sh -c 'mvn -B -q package -DskipTests && pytest -q -m faults'

fault-demo:       ## the original MS2 crash-reassignment oracle, which passes since MS3 leases
	sh deploy/harness/run.sh sh -c 'mvn -B -q package -DskipTests && pytest -q tests/faults/test_worker_crash.py'

bench:            ## fault-free C x W x 5 matrix on capped Compose services; raw + summary in results/benchmark/<UTC time>/
	$(COMPOSE) build
	$(PYTHON) -m benchmarks.run --backend compose --out results/benchmark/$$(date -u +%Y%m%dT%H%M%SZ)

bench-recovery:   ## recovery-time experiment: baseline vs. killed workers, W=4, C in {1,4,16}; results/benchmark/recovery-<UTC time>/
	$(COMPOSE) build
	$(PYTHON) -m benchmarks.recovery --backend compose --out results/benchmark/recovery-$$(date -u +%Y%m%dT%H%M%SZ)

down:             ## stop the deployment; artifact files and results/ are kept
	$(COMPOSE) down
