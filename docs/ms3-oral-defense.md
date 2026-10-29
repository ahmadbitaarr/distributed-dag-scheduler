# MS3 oral defense: preparation sheet

Format (course guidelines): 25 minutes, chalkboard only. One randomly chosen member gives a 10-minute overview of items 1–7 below; then 15 minutes of pointed questions to individual members. Everyone should be able to give the overview.

## The 10-minute overview (one board, left to right)

**1. Design and architecture (2 min).** Draw: client → scheduler ← workers (arrows *into* the scheduler: workers pull) and workers ↔ artifact store. One scheduler process, one mutex, in-memory state. Workers have no inbound port; the scheduler never calls them. Files move only through the immutable artifact store, under per-attempt keys.

**2. Vocabulary (1 min).** Job = DAG of tasks. Attempt = one try of a task, numbered 1, 2, 3… Ownership tuple = (run, job, task, attempt, worker session). Lease = time-limited ownership of an attempt, on the scheduler's clock. Heartbeat = a renewal of the lease. Fencing token = the attempt number: a message carrying an old one is refused.

**3. Functionality (1 min).** Submit a manifest (validated: no cycles, allowlisted operations, size limits) → roots go READY → workers claim (FIFO) → start ack → run → upload outputs → report → children whose parents all succeeded go READY → job done when every task is. Video job: inspect → 720p, 360p, thumbnail, subtitles in parallel → publish.

**4. Safety and liveness (3 min).** Write S1, S2, S3 and L1, L2 on the board.
- S1: only the current, unexpired lease holder's SUCCESS report, with verified outputs, completes a task.
- S2: assigned only after all parents succeeded; executed only after the start ack.
- S3: at most one accepted success per task; one owner at a time.
- L1: with a live worker, every ready task is assigned and eventually succeeds or is retried.
- L2: a crashed, frozen or cut-off worker's task is requeued once its lease expires (5 s) and reassigned.
- Key sentence: *safety never depends on timing; timing only affects how fast we make progress.*

**5. How we think about performance (1 min).** Four metrics, all on the scheduler's clock: job completion time, throughput, scheduling latency (ready → assigned), recovery time (last heartbeat → new owner). Closed-loop load: C concurrent jobs, W workers, 1 CPU / 512 MiB per service.

**6. Performance guarantees (1 min).** We commit to one bound: a crashed worker's task is never declared dead before the 5 s lease, and is reassigned within lease + 2 s when an idle worker is polling. Measured: 5.0–5.1 s. Throughput is a characterization, not a promise: about 4.2 tasks/s per worker on the MS2 host, and it scales with workers until the DAG's own parallelism runs out.

**7. Testing strategy (1 min).** One command, `make test`: 77 JUnit tests (leases tested on a fake clock) and 102 pytest tests against real processes. We inject faults (SIGKILL, SIGSTOP, crash points before start / during / before report, a proxy that drops, delays, duplicates or partitions one worker's link, and a seeded chaos run), and every test runs a checker over the full event history that would flag any S1–S3 violation. The checker is itself tested by injecting violations into a real history.

## Likely questions and short answers

**Why not just reassign after a timeout?** Because a slow worker would then finish too, and two results would compete. Timeouts are fine *if* the old attempt is fenced: its attempt number is now stale, so its report, heartbeat and start are refused, and its files sit under its own attempt prefix where nothing reads them.

**How do you tell a slow worker from a dead one?** We don't, and can't, in an asynchronous network. We only decide "not renewed within 5 s". A slow but live worker keeps renewing (heartbeats run on their own thread), so it keeps its task; the slow-task test runs a task for 2.4 leases without losing it.

**What if a worker's lease expires while it is still working (a false suspicion)?** It may finish and report; the report gets `409 LEASE_EXPIRED` and changes nothing. Cost: repeated work. Tests: lost heartbeats, pause, partition.

**What if the report arrives a millisecond after the deadline, before anyone else took the task?** Rejected anyway. We chose one rule, "expired means dead", over accepting it, because it is simpler to reason about and test. Cost: a re-run in a rare race.

**Is this exactly-once?** Exactly-once *recording* of completion, yes. Execution is at-least-once: an expired attempt can still run. That is fine here because outputs are immutable and per-attempt; it would not be fine for an external side effect like a paid API, which we do not claim.

**Why 5 s / 1 s?** Recovery ≈ lease, so shorter is faster but expires live workers on slow links more often. Five renewals per lease means up to three consecutive lost heartbeats are always tolerated. A false expiry costs work, never correctness, so we leaned toward fewer false expiries.

**Whose clock?** Only the scheduler's monotonic clock decides expiry. Workers never compare clocks with the scheduler; we never subtract timestamps across machines.

**What if the scheduler crashes?** Out of scope by our fault model: a restart is a new, empty run, old messages get `409 STALE_RUN`, and jobs must be resubmitted. Making it durable needs a write-ahead log; replicating it needs consensus.

**What if the scheduler pauses (GC, VM freeze) for longer than the lease?** On resume, every lease looks overdue and live workers' attempts are expired and redone. Safety holds; work is repeated. We list this as a known risk.

**Why a single mutex? Isn't that a bottleneck?** Every decision (claim, success + releasing children, expiry + requeue) is atomic, which is what makes S2 and S3 easy to argue. The benchmark shows an idle worker gets a task in about 5 ms; workers, not the scheduler, limit throughput at our scale.

**What if a message is duplicated or a reply is lost?** Every request carries a stable ID; retries return the stored receipt (`completion_duplicate`), never a second effect. Tested by dropping claim, start and report replies and duplicating every start and report.

**How do you know your tests can fail?** For leases we broke the code on purpose (no renewal; no expiry check before reports) and the tests failed. The history checker is tested by injecting each kind of violation into a real saved history. MS2's crash test failed for real before leases existed.

**What can't you handle?** Scheduler crash, artifact-store loss, malicious workers, a link that drops every report but delivers heartbeats (not fair-loss), and a task that always fails (retried forever; no retry limit).

**What changed since MS2?** Leases, heartbeats and expiry; L2 now holds; 13 new fault tests plus 16 lease unit tests; a fault proxy; recovery-time benchmark; sharper claims (S1 "current unexpired holder", S3 recorded vs. physical, fair-loss stated).
