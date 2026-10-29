package edu.vt.dag;

import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicLong;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
import static edu.vt.dag.Model.*;

/** MS3 leases on an injected clock that moves only when a test says so: no sleeps, no timing flakiness. */
class LeaseTest {
    static final long LEASE = TimeUnit.SECONDS.toNanos(5);
    final AtomicLong time = new AtomicLong();
    final SchedulerCore core = new SchedulerCore(new MemoryStateStore(), time::get, LEASE);

    TaskSpec task(String name, String... parents) {
        return new TaskSpec(name, "fixture_write", new Parameters(3L, null, 0, null), List.of(parents), Map.of(), List.of("value"));
    }
    Manifest manifest(TaskSpec... tasks) {
        return new Manifest(1, UUID.randomUUID(), List.of(tasks), Map.of("result", new OutputBinding(tasks[tasks.length - 1].task_id(), "value")));
    }
    UUID submit(Manifest m) { core.submit(new Submission(core.runId(), m)); return m.job_id(); }
    Assignment claim() { return claim(UUID.randomUUID()); }
    Assignment claim(UUID session) { return core.claim(new Claim(core.runId(), session, UUID.randomUUID())); }
    Report success(Assignment a) {
        return new Report(a.identity(), "SUCCESS", Map.of("value", new Artifact(a.output_prefix() + "value", 1, "0".repeat(64), "application/json")), null);
    }
    Report failure(Assignment a) { return new Report(a.identity(), "FAILURE", Map.of(), new Failure("TEST", "controlled")); }
    void finish(Assignment a) { core.start(a.identity()); core.report(success(a)); }
    void advance(long ns) { time.addAndGet(ns); }
    @SuppressWarnings("unchecked") Map<String, Object> taskSnap(UUID job, String name) {
        return (Map<String, Object>) ((Map<?, ?>) core.snapshot(job).get("tasks")).get(name);
    }
    @SuppressWarnings("unchecked") List<Map<String, Object>> attempts(UUID job, String name) {
        return (List<Map<String, Object>>) taskSnap(job, name).get("attempts");
    }
    @SuppressWarnings("unchecked") List<Map<String, Object>> events() {
        var all = new ArrayList<Map<String, Object>>(); long after = 0; boolean more = true;
        while (more) { var p = core.events(after, 1000); all.addAll((List<Map<String, Object>>) p.get("events"));
            after = ((Number) p.get("next_after")).longValue(); more = (boolean) p.get("has_more"); }
        return all;
    }
    long count(String type) { return events().stream().filter(e -> type.equals(e.get("event_type"))).count(); }
    long counter(String name) { return (Long) ((Map<?, ?>) core.metrics().get("counters")).get(name); }
    String code(Runnable r) { return assertThrows(ApiException.class, r::run).code; }

    // ---- MS2's intentional defect is gone: a silent owner's task is reassigned ----

    @Test void silentOwnerTaskIsReassignedAfterItsLeaseExpires() {
        var job = submit(manifest(task("X"), task("Y", "X")));
        var a = claim(); core.start(a.identity());
        advance(TimeUnit.HOURS.toNanos(24));                   // the owner goes silent
        var b = claim();
        assertEquals("X", b.identity().task_id());
        assertEquals(2, b.identity().attempt_no());
        assertEquals(List.of("EXPIRED", "ASSIGNED"), attempts(job, "X").stream().map(x -> x.get("state").toString()).toList());
        assertEquals(TaskState.BLOCKED, taskSnap(job, "Y").get("state"), "the child still waits for an accepted success");
        var retried = events().stream().filter(e -> "task_retried".equals(e.get("event_type"))).findFirst().orElseThrow();
        assertEquals(AttemptState.EXPIRED, retried.get("previous_attempt_state"));
        finish(b); finish(claim());
        assertEquals(JobState.SUCCEEDED, core.snapshot(job).get("state"));
        assertEquals(2, count("task_succeeded"));
        assertEquals(1L, counter("expired_attempts"));
    }

    @Test void leaseHoldsUntilItsDeadlineExactly() {
        var job = submit(manifest(task("X")));
        var a = claim();
        advance(LEASE - 1);
        assertEquals(0, core.expireLeases());
        assertNull(claim(), "an unexpired lease keeps the task owned");
        advance(1);
        assertEquals(1, core.expireLeases());
        assertEquals(TaskState.READY, taskSnap(job, "X").get("state"));
        assertNull(taskSnap(job, "X").get("owner"));
        assertEquals(0, ((Number) core.metrics().get("active_attempts")).intValue());
        assertEquals("LEASE_EXPIRED", code(() -> core.start(a.identity())));
    }

    @Test void heartbeatsKeepASlowOwnerIndefinitely() {
        var job = submit(manifest(task("X")));
        var a = claim(); core.start(a.identity());
        for (int i = 0; i < 100; i++) { advance(LEASE - 1); assertEquals("RENEWED", core.heartbeat(a.identity()).disposition()); }
        assertNull(claim(), "a slow but live worker keeps its task");
        assertEquals(0, count("lease_expired"));
        core.report(success(a));
        assertEquals(TaskState.SUCCEEDED, taskSnap(job, "X").get("state"));
        assertEquals(100L, counter("lease_renewals"));
        assertEquals(100L, ((Number) attempts(job, "X").get(0).get("lease_renewals")).longValue());
    }

    @Test void startRenewsTheAssignmentLease() {
        submit(manifest(task("X")));
        var a = claim();
        advance(LEASE - 1); core.start(a.identity());
        advance(LEASE - 1); assertEquals(0, core.expireLeases());
        advance(1); assertEquals(1, core.expireLeases());
    }

    @Test void crashBeforeStartExpiresFromAssigned() {
        var job = submit(manifest(task("X")));
        var a = claim();                                       // claimed, never started
        advance(LEASE);
        var b = claim();
        assertEquals(2, b.identity().attempt_no());
        var expired = events().stream().filter(e -> "lease_expired".equals(e.get("event_type"))).findFirst().orElseThrow();
        assertEquals(TaskState.ASSIGNED, expired.get("old_state"));
        assertEquals("LEASE_EXPIRED", code(() -> core.start(a.identity())));
        assertEquals("LEASE_EXPIRED", code(() -> core.heartbeat(a.identity())));
        finish(b);
        assertEquals(JobState.SUCCEEDED, core.snapshot(job).get("state"));
        assertNull(attempts(job, "X").get(0).get("start_receipt"));
    }

    @Test void lateReportsFromAnExpiredAttemptChangeNothing() {
        var job = submit(manifest(task("X")));
        var a = claim(); core.start(a.identity());
        advance(LEASE);
        var b = claim(); core.start(b.identity());
        var before = core.snapshot(job); var metricsBefore = core.metrics(); int eventsBefore = events().size();
        assertEquals("LEASE_EXPIRED", code(() -> core.prepareReport(success(a))));
        assertEquals("LEASE_EXPIRED", code(() -> core.report(success(a))));
        assertEquals("LEASE_EXPIRED", code(() -> core.report(failure(a))));
        assertEquals("LEASE_EXPIRED", code(() -> core.heartbeat(a.identity())));
        assertEquals("LEASE_EXPIRED", code(() -> core.start(a.identity())), "even a replayed start whose ack was cached");
        assertEquals(before, core.snapshot(job));
        assertEquals(eventsBefore, events().size());
        assertEquals(metricsBefore.get("counters"), core.metrics().get("counters"));
        core.report(success(b));
        @SuppressWarnings("unchecked") var outputs = (Map<String, Artifact>) taskSnap(job, "X").get("outputs");
        assertTrue(outputs.get("value").key().contains("/attempts/2/"), "accepted outputs come from the live attempt");
        assertEquals(1, count("task_succeeded"));
    }

    @Test void lateSuccessIsRejectedEvenBeforeAnyoneElseClaims() {
        var job = submit(manifest(task("X")));
        var a = claim(); core.start(a.identity());
        advance(LEASE);                                        // expired; nobody has claimed yet
        assertEquals("LEASE_EXPIRED", code(() -> core.report(success(a))));
        assertEquals(TaskState.READY, taskSnap(job, "X").get("state"));
        assertEquals(1, count("lease_expired"));
    }

    @Test void expiryBetweenPrepareAndCommitRejectsTheSuccess() {
        var job = submit(manifest(task("X")));
        var a = claim(); core.start(a.identity()); var s = success(a);
        assertNull(core.prepareReport(s));                     // artifact HEAD checks happen here, unlocked
        advance(LEASE);
        assertEquals("LEASE_EXPIRED", code(() -> core.report(s)));
        assertEquals(TaskState.READY, taskSnap(job, "X").get("state"));
        assertEquals(0, count("task_succeeded"));
    }

    @Test void acceptedResultsDoNotExpire() {
        var job = submit(manifest(task("X"), task("Y", "X")));
        var a = claim(); core.start(a.identity()); var s = success(a); var ack = core.report(s);
        advance(TimeUnit.HOURS.toNanos(1));
        assertEquals(0, core.expireLeases());
        assertEquals(ack, core.report(s), "a replayed report still gets its receipt");
        assertEquals(TaskState.SUCCEEDED, taskSnap(job, "X").get("state"));
        assertEquals(0, count("lease_expired"));
        assertEquals("CONFLICT", code(() -> core.heartbeat(a.identity())));
    }

    @Test void expiredSessionMayClaimAgainButOnlyAsANewAttempt() {
        var job = submit(manifest(task("X")));
        var session = UUID.randomUUID();
        var first = claim(session); core.start(first.identity());
        advance(LEASE);
        var second = claim(session);                           // e.g. a paused worker that resumes
        assertEquals(2, second.identity().attempt_no());
        assertEquals("LEASE_EXPIRED", code(() -> core.report(success(first))));
        finish(second);
        assertEquals(JobState.SUCCEEDED, core.snapshot(job).get("state"));
    }

    @Test void claimReplayAfterExpiryReportsTerminalExpired() {
        submit(manifest(task("X")));
        var c = new Claim(core.runId(), UUID.randomUUID(), UUID.randomUUID());
        assertEquals("EXECUTE", core.claim(c).disposition());
        advance(LEASE);
        assertEquals("TERMINAL_EXPIRED", core.claim(c).disposition());
    }

    @Test void heartbeatFromNonOwnersIsRejected() {
        submit(manifest(task("X")));
        var a = claim(); var id = a.identity();
        var stranger = new Identity(id.scheduler_run_id(), id.job_id(), id.task_id(), id.attempt_no(), UUID.randomUUID());
        assertEquals("CONFLICT", code(() -> core.heartbeat(stranger)));
        assertEquals("CONFLICT", code(() -> core.heartbeat(new Identity(id.scheduler_run_id(), id.job_id(), "X", 2, id.worker_session_id()))));
        assertEquals("STALE_RUN", code(() -> core.heartbeat(new Identity(UUID.randomUUID(), id.job_id(), "X", 1, id.worker_session_id()))));
        assertEquals(0L, counter("lease_renewals"));
    }

    @Test void expiredTasksRejoinTheFifoTailInAssignmentOrder() {
        submit(manifest(task("A"), task("B"), task("C")));
        var a = claim(); var b = claim();                      // C stays queued
        advance(LEASE);
        assertEquals(2, core.expireLeases());
        assertEquals(List.of("C", "A", "B"), List.of(claim().identity().task_id(), claim().identity().task_id(), claim().identity().task_id()));
        assertNotNull(a); assertNotNull(b);
    }

    @Test void recoveryLatencyIsMeasuredFromLastSignOfLifeOnTheSchedulerClock() {
        submit(manifest(task("X")));
        var a = claim(); core.start(a.identity());
        advance(1_000); core.heartbeat(a.identity());          // last sign of life at t=1000
        advance(LEASE + 250_000_000L);                         // expiry plus 250 ms until an idle worker claims
        claim();
        var recovery = (Map<?, ?>) core.metrics().get("lease_recovery_ns");
        assertEquals(1, recovery.get("count"));
        assertEquals(LEASE + 250_000_000L, ((Number) recovery.get("p50")).longValue());
    }

    @Test void explicitFailureStillRetriesWithoutWaitingForTheLease() {
        var job = submit(manifest(task("X")));
        var a = claim(); core.report(failure(a));
        assertEquals(2, claim().identity().attempt_no());
        assertEquals(0, count("lease_expired"));
        assertEquals(1L, counter("explicit_failed_attempts"));
        assertEquals(TaskState.ASSIGNED, taskSnap(job, "X").get("state"));
    }

    @Test void racingCrashesExpiriesAndReportsKeepOneSuccessPerTask() throws Exception {
        // Every command advances the clock; a quarter of attempts are abandoned (a crash), and the
        // short lease also expires some live attempts mid-flight. Safety must hold either way.
        var clock = new AtomicLong();
        var racing = new SchedulerCore(new MemoryStateStore(), () -> clock.addAndGet(1_000), 2_000_000L);
        var jobs = new ArrayList<UUID>();
        for (int i = 0; i < 15; i++) {
            var m = manifest(task("A"), task("B", "A"), task("C", "A"), task("D", "B", "C"));
            racing.submit(new Submission(racing.runId(), m)); jobs.add(m.job_id());
        }
        var stop = new java.util.concurrent.atomic.AtomicBoolean();
        try (var pool = Executors.newFixedThreadPool(9)) {
            var scanner = pool.submit(() -> { while (!stop.get()) { racing.expireLeases(); Thread.sleep(1); } return null; });
            var workers = new ArrayList<Future<?>>();
            for (int w = 0; w < 8; w++) {
                long seed = w;
                workers.add(pool.submit(() -> {
                    var random = new Random(seed); var session = UUID.randomUUID();
                    long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(20);
                    while (System.nanoTime() < deadline && jobs.stream().anyMatch(j -> racing.snapshot(j).get("state") != JobState.SUCCEEDED)) {
                        var a = racing.claim(new Claim(racing.runId(), session, UUID.randomUUID()));
                        if (a == null || !a.disposition().equals("EXECUTE")) continue;
                        if (random.nextInt(4) == 0) { session = UUID.randomUUID(); continue; }   // crash: abandon, restart as new session
                        try {
                            racing.start(a.identity());
                            racing.report(new Report(a.identity(), "SUCCESS", Map.of("value",
                                new Artifact(a.output_prefix() + "value", 1, "0".repeat(64), "application/json")), null));
                        } catch (ApiException e) {
                            assertEquals(409, e.status, "only lease/ownership conflicts are expected");
                        }
                    }
                    return null;
                }));
            }
            for (var f : workers) f.get(30, TimeUnit.SECONDS);
            stop.set(true); scanner.get(5, TimeUnit.SECONDS);
        }
        for (var job : jobs) assertEquals(JobState.SUCCEEDED, racing.snapshot(job).get("state"));
        @SuppressWarnings("unchecked") List<Map<String, Object>> evs = (List<Map<String, Object>>) racing.events(0, 1000).get("events");
        var all = new ArrayList<Map<String, Object>>(evs);
        for (long after = all.size(); ; after = all.size()) {
            @SuppressWarnings("unchecked") var page = (List<Map<String, Object>>) racing.events(after, 1000).get("events");
            if (page.isEmpty()) break; all.addAll(page);
        }
        var successes = all.stream().filter(e -> "task_succeeded".equals(e.get("event_type"))).toList();
        assertEquals(15 * 4, successes.size());
        assertEquals(15 * 4, successes.stream().map(e -> e.get("job_id") + "/" + e.get("task_id")).distinct().count());
        var expired = new HashSet<String>();
        for (var e : all) {
            String attempt = e.get("job_id") + "/" + e.get("task_id") + "/" + e.get("attempt_no");
            if ("lease_expired".equals(e.get("event_type"))) expired.add(attempt);
            if ("task_succeeded".equals(e.get("event_type"))) assertFalse(expired.contains(attempt), "success from an expired attempt " + attempt);
        }
        assertFalse(expired.isEmpty(), "the race must actually exercise expiry");
    }
}
