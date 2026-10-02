package edu.vt.dag;

import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicLong;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
import static edu.vt.dag.Model.*;

/** Step 3 contract checks for architecture §§4, 5, 7 beyond SchedulerCoreTest. */
class SchedulerStateMachineTest {
    final AtomicLong time = new AtomicLong();
    final SchedulerCore core = new SchedulerCore(new MemoryStateStore(), () -> time.addAndGet(100));

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
    @SuppressWarnings("unchecked") Map<String, Object> taskSnap(UUID job, String name) {
        return (Map<String, Object>) ((Map<?, ?>) core.snapshot(job).get("tasks")).get(name);
    }
    @SuppressWarnings("unchecked") List<Map<String, Object>> events() {
        var all = new ArrayList<Map<String, Object>>(); long after = 0; boolean more = true;
        while (more) { var p = core.events(after, 1000); all.addAll((List<Map<String, Object>>) p.get("events"));
            after = ((Number) p.get("next_after")).longValue(); more = (boolean) p.get("has_more"); }
        return all;
    }
    long count(String type) { return events().stream().filter(e -> type.equals(e.get("event_type"))).count(); }
    long counter(String name) { return (Long) ((Map<?, ?>) core.metrics().get("counters")).get(name); }

    // ---- the deliberate MS2 liveness defect ----

    @Test void silentOwnerKeepsTaskForeverEvenAsTimePasses() {
        var job = submit(manifest(task("X"), task("Y", "X")));
        var a = claim(); core.start(a.identity());
        time.addAndGet(TimeUnit.HOURS.toNanos(24));          // the owning worker goes silent
        for (int i = 0; i < 50; i++) assertNull(claim(), "no silent-owner reassignment in MS2");
        assertEquals(TaskState.RUNNING, taskSnap(job, "X").get("state"));
        assertEquals(a.identity().worker_session_id(), taskSnap(job, "X").get("owner"));
        assertEquals(TaskState.BLOCKED, taskSnap(job, "Y").get("state"));
        assertEquals(JobState.RUNNING, core.snapshot(job).get("state"));
        assertEquals(1, taskSnap(job, "X").get("attempt_no"));
    }

    // ---- atomicity: rejected commands do not change scheduling state ----

    @Test void rejectedCommandsLeaveStateAndEventsUnchanged() {
        var job = submit(manifest(task("A"), task("B", "A")));
        var a = claim();
        var before = core.snapshot(job); int eventsBefore = events().size(); var metricsBefore = core.metrics();
        var id = a.identity();
        var stranger = new Identity(id.scheduler_run_id(), id.job_id(), id.task_id(), id.attempt_no(), UUID.randomUUID());
        assertThrows(ApiException.class, () -> core.report(success(a)));                                         // success before RUNNING
        assertThrows(ApiException.class, () -> core.start(stranger));                                            // wrong owner
        assertThrows(ApiException.class, () -> core.report(new Report(stranger, "FAILURE", Map.of(), new Failure("X", "y"))));
        assertThrows(ApiException.class, () -> core.start(new Identity(id.scheduler_run_id(), id.job_id(), "A", 2, id.worker_session_id()))); // unknown attempt
        assertThrows(ApiException.class, () -> core.start(new Identity(id.scheduler_run_id(), id.job_id(), "B", 1, id.worker_session_id())));  // blocked task
        assertThrows(ApiException.class, () -> core.claim(new Claim(UUID.randomUUID(), UUID.randomUUID(), UUID.randomUUID())));            // stale run
        assertThrows(ApiException.class, () -> core.submit(new Submission(UUID.randomUUID(), manifest(task("Z")))));
        assertEquals(before, core.snapshot(job));
        assertEquals(eventsBefore, events().size());
        assertEquals(metricsBefore.get("counters"), core.metrics().get("counters"));
        assertEquals(metricsBefore.get("tasks_by_state"), core.metrics().get("tasks_by_state"));
    }

    @Test void startAfterExplicitFailureIsStale() {
        submit(manifest(task("A")));
        var a = claim(); core.report(failure(a));              // failure directly from ASSIGNED
        assertThrows(ApiException.class, () -> core.start(a.identity()));
    }

    // ---- retries ----

    @Test void oldDuplicateFailureDoesNotDisturbNewerAttempt() {
        var job = submit(manifest(task("A")));
        var first = claim(); core.start(first.identity()); var f = failure(first); var receipt = core.report(f);
        var second = claim(); core.start(second.identity());
        assertEquals(2, second.identity().attempt_no());
        assertEquals(receipt, core.report(f));                 // replay of attempt-1 failure
        assertEquals(TaskState.RUNNING, taskSnap(job, "A").get("state"));
        assertEquals(second.identity().worker_session_id(), taskSnap(job, "A").get("owner"));
        assertNull(claim(), "replay must not requeue the task again");
        assertThrows(ApiException.class, () -> core.report(success(first)));      // late success from failed attempt
        core.report(success(second));
        assertEquals(TaskState.SUCCEEDED, taskSnap(job, "A").get("state"));
        assertEquals(1, count("task_retried"));
        assertEquals(1L, counter("explicit_failed_attempts"));
        assertEquals(1L, counter("accepted_logical_successes"));
        assertTrue(counter("duplicate_reports") >= 1);
    }

    @Test void repeatedFailuresKeepIncreasingAttemptNumbersWithoutRetryCap() {
        var job = submit(manifest(task("A")));
        for (int n = 1; n <= 5; n++) {
            var a = claim(); assertEquals(n, a.identity().attempt_no());
            if (n % 2 == 0) core.start(a.identity());          // alternate failure from ASSIGNED and RUNNING
            core.report(failure(a));
            assertEquals(TaskState.READY, taskSnap(job, "A").get("state"));
        }
        assertEquals(JobState.RUNNING, core.snapshot(job).get("state"));   // no terminal FAILED job
        finish(claim());
        assertEquals(JobState.SUCCEEDED, core.snapshot(job).get("state"));
    }

    // ---- dependency accounting and ordering ----

    @Test void duplicateSuccessSatisfiesEachEdgeExactlyOnce() {
        var job = submit(manifest(task("A"), task("B", "A"), task("C", "A")));
        var a = claim(); core.start(a.identity()); var s = success(a); var ack = core.report(s);
        for (int i = 0; i < 3; i++) { assertEquals(ack, core.prepareReport(s)); assertEquals(ack, core.report(s)); }
        assertEquals(2, count("dependency_satisfied"));
        assertEquals(1, count("task_succeeded"));
        assertEquals(List.of("A"), taskSnap(job, "B").get("satisfied_parents"));
        // B and C each enqueued exactly once.
        assertNotNull(claim()); assertNotNull(claim()); assertNull(claim());
    }

    @Test void releasedChildrenAndRootsEnqueueInDeterministicOrder() {
        var j1 = submit(manifest(task("R"), task("z", "R"), task("b", "R"), task("M", "R")));
        var j2 = submit(manifest(task("Q2"), task("Q1")));
        var r = claim(); assertEquals("R", r.identity().task_id());
        assertEquals(List.of("Q1", "Q2"), List.of(claim().identity().task_id(), claim().identity().task_id()));
        finish(r);
        var order = new ArrayList<String>();
        for (int i = 0; i < 3; i++) order.add(claim().identity().task_id());
        assertEquals(List.of("M", "b", "z"), order);           // task-ID order within one release
        var seqs = events().stream().filter(e -> "task_ready".equals(e.get("event_type")))
            .map(e -> ((Number) e.get("ready_seq")).longValue()).toList();
        for (int i = 1; i < seqs.size(); i++) assertEquals(seqs.get(i - 1) + 1, seqs.get(i));
        assertNotNull(j1); assertNotNull(j2);
    }

    @Test void jobSucceedsOnlyWhenEveryTaskSucceeds() {
        var job = submit(manifest(task("A"), task("B")));      // disconnected; final output names only B
        var first = claim(); var second = claim();
        var b = first.identity().task_id().equals("B") ? first : second;
        var a = b == first ? second : first;
        finish(b);
        assertEquals(JobState.RUNNING, core.snapshot(job).get("state"));
        assertEquals(Map.of(), core.snapshot(job).get("outputs"));
        finish(a);
        assertEquals(JobState.SUCCEEDED, core.snapshot(job).get("state"));
        assertEquals(1, count("job_completed"));
    }

    // ---- sessions ----

    @Test void sessionHoldsOneActiveAttemptAndGetsItBackOnNewClaims() {
        submit(manifest(task("A"), task("B")));
        var session = UUID.randomUUID();
        var a = claim(session);
        assertEquals(a.identity(), claim(session).identity());
        assertEquals(a.identity(), claim(session).identity());
        var other = claim();
        assertNotEquals(a.identity().task_id(), other.identity().task_id());
        finish(a);
        assertNull(claim(session), "both tasks are taken");
    }

    // ---- submissions ----

    @Test void submissionReplayIsIdempotentAndConflictIsRejected() {
        var m = manifest(task("A"));
        assertEquals(201, core.submit(new Submission(core.runId(), m)).status());
        int events = events().size();
        assertEquals(200, core.submit(new Submission(core.runId(), m)).status());
        assertEquals(200, core.submissionReplay(new Submission(core.runId(), m)).status());
        assertEquals(events, events().size());
        var changed = new Manifest(1, m.job_id(), List.of(new TaskSpec("A", "fixture_write", new Parameters(4L, null, 0, null), List.of(), Map.of(), List.of("value"))), m.final_outputs());
        assertEquals(409, assertThrows(ApiException.class, () -> core.submit(new Submission(core.runId(), changed))).status);
        assertEquals(1L, counter("accepted_jobs"));
    }

    // ---- report shape ----

    @Test void reportOutputsMustMatchDeclaredNamesAndAttemptNamespace() {
        submit(manifest(task("A")));
        var a = claim(); core.start(a.identity()); var id = a.identity();
        var art = new Artifact(a.output_prefix() + "value", 1, "0".repeat(64), "application/json");
        var otherAttempt = new Artifact(a.output_prefix().replace("/attempts/1/", "/attempts/2/") + "value", 1, "0".repeat(64), "application/json");
        for (var bad : List.of(
                new Report(id, "SUCCESS", Map.of(), null),
                new Report(id, "SUCCESS", Map.of("value", art, "extra", art), null),
                new Report(id, "SUCCESS", Map.of("value", otherAttempt), null),
                new Report(id, "SUCCESS", Map.of("value", art), new Failure("X", "y")),
                new Report(id, "FAILURE", Map.of("value", art), new Failure("X", "y")),
                new Report(id, "FAILURE", Map.of(), null),
                new Report(id, "FAILURE", Map.of(), new Failure("bad code", "y")),
                new Report(id, "FAILURE", Map.of(), new Failure("X", "y".repeat(2049))),
                new Report(id, "MAYBE", Map.of(), null)))
            assertEquals(400, assertThrows(ApiException.class, () -> core.report(bad)).status);
        core.report(new Report(id, "SUCCESS", Map.of("value", art), null));
    }

    // ---- concurrency stress ----

    @Test void concurrentWorkersCompleteManyJobsWithOneSuccessPerTask() throws Exception {
        var jobs = new ArrayList<UUID>();
        for (int i = 0; i < 20; i++)
            jobs.add(submit(manifest(task("A"), task("B", "A"), task("C", "A"), task("D", "A"), task("E", "B", "C", "D"), task("F", "E"))));
        try (var pool = Executors.newFixedThreadPool(8)) {
            var futures = new ArrayList<Future<?>>();
            for (int w = 0; w < 8; w++) futures.add(pool.submit(() -> {
                var session = UUID.randomUUID(); int idle = 0;
                while (idle < 200) {
                    var a = claim(session);
                    if (a == null) { idle++; Thread.onSpinWait(); continue; }
                    idle = 0; core.start(a.identity());
                    if (a.identity().attempt_no() == 1 && a.identity().task_id().equals("C")) core.report(failure(a));
                    else core.report(success(a));
                }
                return null;
            }));
            for (var f : futures) f.get(30, TimeUnit.SECONDS);
        }
        for (var job : jobs) assertEquals(JobState.SUCCEEDED, core.snapshot(job).get("state"));
        var evs = events();
        assertEquals(20 * 6, evs.stream().filter(e -> "task_succeeded".equals(e.get("event_type"))).count());
        assertEquals(20 * 6, evs.stream().filter(e -> "task_succeeded".equals(e.get("event_type")))
            .map(e -> e.get("job_id") + "/" + e.get("task_id")).distinct().count());
        assertEquals(20, evs.stream().filter(e -> "task_retried".equals(e.get("event_type"))).count());
        // Every child's assignment follows the success of all its parents in the scheduler sequence.
        var successSeq = new HashMap<String, Long>();
        for (var e : evs) {
            String key = e.get("job_id") + "/" + e.get("task_id");
            long seq = ((Number) e.get("scheduler_event_seq")).longValue();
            if ("task_succeeded".equals(e.get("event_type"))) successSeq.put(key, seq);
            if ("task_assigned".equals(e.get("event_type"))) {
                var parents = Map.of("A", List.<String>of(), "B", List.of("A"), "C", List.of("A"), "D", List.of("A"), "E", List.of("B", "C", "D"), "F", List.of("E"))
                    .get((String) e.get("task_id"));
                for (String p : parents) {
                    Long ps = successSeq.get(e.get("job_id") + "/" + p);
                    assertNotNull(ps, "parent " + p + " not succeeded before " + key);
                    assertTrue(ps < seq);
                }
            }
        }
        assertEquals(0, ((Number) core.metrics().get("active_attempts")).intValue());
        assertEquals(0, ((Number) core.metrics().get("ready_queue_length")).intValue());
    }
}
