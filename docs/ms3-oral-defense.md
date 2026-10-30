# MS3 oral defense: preparation sheet

Use this to practise explaining the system, then answer in your own words. Our recorded course format is 25 minutes, chalkboard only: a randomly chosen member gives a 10-minute overview, followed by 15 minutes of questions to individuals. Both of us need to understand the whole design.

## The 10-minute overview

### 1. Design and architecture (2 min)

Draw the client, scheduler, workers and artifact store. Show claim, start, heartbeat and report arrows going into the scheduler because workers pull. We chose one scheduler, one mutex and in-memory state. Workers have no inbound task-control port. Inputs and outputs go through the immutable artifact store, under separate keys for each attempt.

### 2. Vocabulary (1 min)

A job is a DAG of tasks. An attempt is one execution assignment, numbered 1, 2, 3… The ownership tuple is (run, job, task, attempt, worker session). A lease gives the attempt time-limited ownership on the scheduler's clock; a heartbeat renews it. The attempt number is our fencing token, so an expired attempt cannot later decide the task's result.

### 3. Functionality (1 min)

The client submits a manifest. We reject cycles, unsupported operations and oversized inputs. Roots become READY. Workers claim from the FIFO, wait for a start acknowledgment, execute, upload outputs and report. A successful report can release children; the job finishes only after every task succeeds. Our video DAG is inspect → 720p, 360p, thumbnail and fixture subtitles in parallel → publish.

### 4. Safety and liveness (3 min)

Write S1, S2, S3, L1 and L2 on the board and explain the distinction.

- S1: only a valid SUCCESS from the current, unexpired lease holder, with verified outputs, completes a task.
- S2: assignment waits for all parent successes; execution waits for the start acknowledgment.
- S3: one accepted success per logical task and one active owner, even if execution repeats.
- L1: with available services, eventual communication and adequate execution intervals, ready work is assigned and succeeds or is retried.
- L2: a crashed, frozen or disconnected worker's unfinished task returns to the queue after its lease expires (default 5 s).

Safety comes from atomic ownership and state checks. Timing affects progress and how often work is repeated. We do not need synchronized clocks.

### 5. How we measure performance (1 min)

Explain the four scheduler-clock metrics: job completion time, throughput, scheduling latency (ready → assigned), and recovery (last accepted renewal → new owner). Recovery does not start at the external kill command. The load driver keeps C jobs in flight on W workers, with 1 CPU and 512 MiB per service.

### 6. Performance guarantees (1 min)

P-REC says we do not detect expiry before the 5 s lease, and require reassignment within lease + 2 s when an idle worker is polling under the stated conditions. The completed benchmark measured 5.0–5.1 s with a free worker. One queued task took 10.3 s with all workers busy. The benchmark completed 17 of 18 runs; explain the driver's timeout rather than calling all 18 complete. Throughput is a characterization: about 4.2 tasks/s per worker in the MS2 measurements, with limits from the workload and host.

### 7. Testing strategy (1 min)

`make test` runs 77 JUnit tests and 107 pytest tests. The final log records 105 passed, 2 skipped (they need a local Hokea install), and no failures or expected failures. Lease unit tests use an injected clock. Service-backed tests use real processes and inject SIGKILL, SIGSTOP, stage-specific stalls, message loss, delay, duplication and partitions, plus a seeded chaos run. We check the exported histories for S1–S3. Checker tests deliberately corrupt a saved history and require rejection.

## Questions to practise

**Why not just reassign after a timeout?**

We do reassign after timeout, but also fence the old attempt. A slow worker may still finish. Its attempt number is no longer current, so its start, heartbeat and report are refused. Its output prefix is separate and does not overwrite the accepted files.

**How do you tell a slow worker from a dead one?**

We cannot know from silence alone. We know only that no renewal arrived within 5 s. A slow worker can keep its attempt through its heartbeat thread. The slow-task test runs for 2.4 leases without expiry.

**What happens on false suspicion?**

The old worker may finish, but its report receives `409 LEASE_EXPIRED`. We repeat work rather than accepting two results. Lost-heartbeat, pause and partition tests exercise this.

**What if success arrives a millisecond late and nobody else has claimed?**

We still reject it. A single expiry rule is easier to explain and test than a special case for tasks not yet reassigned. The cost is an occasional re-run.

**Is this exactly-once?**

We guarantee at most one recorded success for a logical task. With the liveness assumptions and an operation that can succeed, the job eventually gets its result. Physical execution is at-least-once: an expired attempt may continue running. Immutable per-attempt files make that acceptable here. We do not promise exactly-once paid API calls or other external effects.

**Why a 5 s lease and 1 s heartbeat?**

A shorter lease recovers sooner but is less tolerant of delay. With prompt heartbeat requests, three consecutive lost renewals fit inside the default lease. This is not an unconditional guarantee: the worker waits after each request finishes, so a long request or timeout can consume the margin. False expiry costs work, not a second accepted completion.

**Whose clock decides?**

The scheduler's monotonic clock. Workers do not compare their clocks to it, and measurements never subtract timestamps from separate machines.

**What if the scheduler crashes?**

Scheduler recovery is outside our fault model. A restart creates a new, empty run; old messages receive `409 STALE_RUN`, and jobs need resubmission. Durable state and replicated failover would require separate design work, such as a write-ahead log or consensus.

**What if the scheduler pauses longer than the lease?**

When it resumes, leases look overdue and live attempts may be expired and repeated. Ownership checks still protect safety. We list this risk in the report.

**Does the single mutex limit performance?**

It makes assignment, completion with dependency release, and expiry with requeue atomic. The earlier benchmark measured about 5 ms ready-to-assigned latency with an idle worker, suggesting workers were the main limit at that scale. We have not proved the scheduler can handle arbitrary load.

**What if a message or reply is lost or duplicated?**

Retries retain their job, claim or attempt identity. The scheduler uses receipts so a replay does not repeat its state change (`completion_duplicate`). We test lost claim, start and report replies and duplicated starts and reports. Empty-claim receipts are bounded per session after the memory fix; they are not an unlimited archive of idle polls.

**How do you know the tests detect defects?**

Deliberately disabling renewal and removing report-time expiry checks made lease tests fail. Checker tests inject specific violations into a real history. The original crash test also failed in MS2 before recovery existed.

**What do the benchmark's interrupted runs mean?**

The selected experiment completed 17 of 18 runs. One event-stream read timed out in the driver; its 27 submitted jobs finished, but it did not complete the planned benchmark phase and is excluded from the summary. Earlier attempts are kept and labeled separately. The retained scheduler histories of all 18 selected runs pass the offline checker, covering 503 jobs. That does not turn an incomplete benchmark into a complete one.

**What cannot the system handle?**

Scheduler crash recovery, artifact-store loss and malicious workers are out of scope. A link dropping every report while delivering heartbeats violates fair-loss assumptions and can stall completion. A task that always fails retries forever. Histories grow with real work; the memory probe suggests about 11,000 tasks per run with the 128 MiB heap.

**Does it run on the course cluster?**

Yes. The smoke test, the functional workload, the crash oracle and the instructor's bounded re-run test pass on Hokea, with crashes done by force-deleting the pod; recovery there took 5.1–5.6 s. The MS2 "version mismatch" was our bug: we required Hokea to match a public commit byte for byte, and the runner's build differs. We now check only for the Hokea calls we make.

**What changed since MS2?**

Leases, heartbeats and expiry fixed the stuck-task case. We added 16 lease unit tests, an idle-polling test, 14 fault tests (one is the instructor's), 2 checker tests, the fault proxy and recovery benchmark. We also fixed replayed-start handling after expiry, the idle-polling memory leak, and the Hokea adapter. The specification now separates recorded completion from physical execution and states the fault assumptions more precisely.
