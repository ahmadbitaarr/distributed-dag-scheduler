# MS2 evaluator commands (architecture §15). Run from the repository root.
# fault-demo (Step 10) and bench (Step 12) are added at those roadmap steps.
COMPOSE = docker compose -f deploy/compose/compose.yaml
WORKERS ?= 3
PYTHON ?= python3

.PHONY: build up demo test down

build:            ## compile and run the JUnit tests
	mvn -B verify

up:               ## build images, start scheduler + artifact store + $(WORKERS) workers, wait for readiness
	$(COMPOSE) up -d --build --wait --scale worker=$(WORKERS) scheduler artifact-store worker

demo:             ## run the functional and video demos against `make up`; outputs in results/demo/
	$(PYTHON) -m tests.harness.demo

test:             ## JUnit + full pytest suite in the Linux harness container; requires exactly one XFAIL
	sh deploy/harness/run.sh

down:             ## stop the deployment; artifact files and results/ are kept
	$(COMPOSE) down
