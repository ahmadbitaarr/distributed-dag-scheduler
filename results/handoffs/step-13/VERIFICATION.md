# Step 13 Independent Clean-Checkout Verification

## Tested revision

- Git SHA: `f27aec9e1230b07c191f34f6a2278eafb0351f4f`
- Branch: `main`
- Verification performed from a fresh clone at `/home/ahmad/step13-verification/distributed-dag-scheduler`.

## Environment

- OS: Ubuntu 24.04.4 LTS (Noble Numbat)
- Docker: 29.7.2, build `a7dcaa6`
- Docker Compose: v5.5.1
- Python: 3.12.3

## Verification results

### Full test suite

`make test`

- 87 tests collected
- 86 passed
- 1 xfailed
- 0 failures
- Expected XFAIL: `tests/faults/test_worker_crash.py::test_worker_crash_reassignment`
- Reason: `MS2 deliberately omits silent-worker ownership reclamation`
- A transient `java.io.IOException: connection closed before all data received` harness log appeared but caused no test failure.

### Intentional correctness failure

`make fault-demo`

- Failed as expected with `RecoveryNotObserved`.
- Captured output ended with `1 failed in 17.90s` and `make: *** [Makefile:21: fault-demo] Error 1`.
- Exact shell `$?` was not preserved because `clear` was run before checking it.
- Task X remained RUNNING under killed worker A rather than being reassigned to healthy worker B within the controlled 10-second window.

### Functional and media demo

`make up` and `make demo`

- Functional result: `result=22`
- Scheduler run: `2987365d-7e0c-42c1-be36-b5b2fa4ea910`
- Video job duration: 5269.156871 ms
- History checks: passed
- `video720.mp4`: H.264, 1280x720
- `video360.mp4`: H.264, 640x360
- `thumbnail.png`: PNG, 1280x720
- `subtitles.srt` generated
- `make down` completed successfully.

### Evidence validation

Every directory under `results/latest-tests` containing `manifests.json` was checked with `python3 -m tests.harness.check_evidence`.

- 40 evidence directories checked
- Every directory reported `OK`
- No evidence-check failures
- Includes the intentional runxfail worker-crash evidence

### Benchmark reproduction

Command:

`python3 -m benchmarks.run --backend compose --out results/benchmark/verify-1 --configs c1-w1 --repetitions 1`

Observed:

- Configuration: `c1-w1-r1`
- Status: complete
- Completed jobs: 24
- Tasks/second: 3.6789568629381906
- Job p50: 1605.221847 ms
- Scheduling p50: 24.604612 ms
- Wall time: 76.5 s
- Error: null

## Findings

Independent clean-checkout verification passed all intended Step 13 gates. The full suite passes with exactly one intentional XFAIL; the worker-crash reassignment property fails as designed for MS2; functional and media outputs are correct; generated histories pass the evidence checks; and the benchmark verification completes successfully.

No implementation changes were required during Step 13.
