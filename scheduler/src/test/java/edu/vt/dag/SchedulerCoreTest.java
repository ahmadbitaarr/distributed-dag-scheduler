package edu.vt.dag;

import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicLong;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
import static edu.vt.dag.Model.*;

class SchedulerCoreTest {
    final AtomicLong time=new AtomicLong();
    final SchedulerCore core=new SchedulerCore(new MemoryStateStore(),()->time.addAndGet(100));
    TaskSpec task(String name,String...parents) {return new TaskSpec(name,"fixture_write",new Parameters(3L,null,0,null),List.of(parents),Map.of(),List.of("value"));}
    Manifest manifest(TaskSpec...tasks) {return new Manifest(1,UUID.randomUUID(),List.of(tasks),Map.of("result",new OutputBinding(tasks[tasks.length-1].task_id(),"value")));}
    UUID submit(Manifest m){core.submit(new Submission(core.runId(),m));return m.job_id();}
    Assignment claim(){return core.claim(new Claim(core.runId(),UUID.randomUUID(),UUID.randomUUID()));}
    Report success(Assignment a){return new Report(a.identity(),"SUCCESS",Map.of("value",new Artifact(a.output_prefix()+"value",1,"0".repeat(64),"application/json")),null);}
    Report failure(Assignment a){return new Report(a.identity(),"FAILURE",Map.of(),new Failure("TEST","controlled"));}
    void finish(Assignment a){core.start(a.identity());core.report(success(a));}
    @SuppressWarnings("unchecked") Map<String,Object> taskSnapshot(UUID id,String name){return (Map<String,Object>)((Map<?,?>)core.snapshot(id).get("tasks")).get(name);}

    @Test void legalTransitionsJoinFifoAndAllTasksCompletion(){
        var m=manifest(task("A"),task("B","A"),task("C","A"),task("D","B","C"));var id=submit(m);
        assertEquals(TaskState.READY,taskSnapshot(id,"A").get("state"));assertEquals(TaskState.BLOCKED,taskSnapshot(id,"D").get("state"));
        var a=claim();assertEquals("A",a.identity().task_id());assertEquals(JobState.RUNNING,core.snapshot(id).get("state"));finish(a);
        var b=claim();var c=claim();assertEquals("B",b.identity().task_id());assertEquals("C",c.identity().task_id());
        finish(c);assertEquals(TaskState.BLOCKED,taskSnapshot(id,"D").get("state"));assertNull(claim());
        finish(b);var d=claim();assertEquals("D",d.identity().task_id());finish(d);
        assertEquals(JobState.SUCCEEDED,core.snapshot(id).get("state"));assertTrue((Long)core.snapshot(id).get("duration_ns")>0);
    }

    @Test void rejectsSuccessBeforeStartWrongOwnerAndStaleRun(){
        submit(manifest(task("A")));var a=claim();assertThrows(ApiException.class,()->core.report(success(a)));
        var id=a.identity();var stranger=new Identity(id.scheduler_run_id(),id.job_id(),id.task_id(),id.attempt_no(),UUID.randomUUID());
        assertThrows(ApiException.class,()->core.start(stranger));
        assertThrows(ApiException.class,()->core.start(new Identity(UUID.randomUUID(),id.job_id(),id.task_id(),1,id.worker_session_id())));
        core.start(id);assertEquals(core.start(id),core.start(id));
        assertThrows(ApiException.class,()->core.report(new Report(id,"SUCCESS",Map.of(),null)));
        assertThrows(ApiException.class,()->core.report(new Report(id,null,Map.of(),null)));
    }

    @Test void duplicateFailureRequeuesOnlyOnceAndSuccessReceiptIsTerminal(){
        var id=submit(manifest(task("A"),task("B","A")));var a=claim();var f=failure(a);
        var receipt=core.report(f);assertEquals(receipt,core.report(f));
        var next=claim();assertEquals(2,next.identity().attempt_no());assertNull(claim());
        assertEquals(receipt,core.report(f));assertThrows(ApiException.class,()->core.report(success(a)));
        core.start(next.identity());var s=success(next);var success=core.report(s);assertEquals(success,core.report(s));
        assertThrows(ApiException.class,()->core.report(failure(next)));
        assertEquals(List.of("A"),taskSnapshot(id,"B").get("satisfied_parents"));
        assertEquals(1L,((Map<?,?>)core.metrics().get("counters")).get("accepted_logical_successes"));
    }

    @Test void failureFromRunningGoesToFifoTail(){
        submit(manifest(task("A"),task("B")));var a=claim();core.start(a.identity());core.report(failure(a));
        assertEquals("B",claim().identity().task_id());assertEquals("A",claim().identity().task_id());
    }

    @Test void allClaimsAreAtomicAndOneActiveAttemptPerSession()throws Exception{
        submit(manifest(task("A")));try(var pool=Executors.newFixedThreadPool(16)){
            var futures=new ArrayList<Future<Assignment>>();for(int i=0;i<32;i++)futures.add(pool.submit(this::claim));
            var assigned=new ArrayList<Assignment>();for(var f:futures){var a=f.get();if(a!=null)assigned.add(a);}
            assertEquals(1,assigned.size());var a=assigned.getFirst();
            assertEquals(a.identity(),core.claim(new Claim(core.runId(),a.identity().worker_session_id(),UUID.randomUUID())).identity());
        }
    }

    @Test void successRevalidatesAfterConcurrentFailure(){
        submit(manifest(task("A")));var a=claim();core.start(a.identity());var s=success(a);
        assertNull(core.prepareReport(s)); // External HEAD checks occur here, with no lock held.
        core.report(failure(a));assertThrows(ApiException.class,()->core.report(s));
        assertEquals(TaskState.READY,taskSnapshot(a.identity().job_id(),"A").get("state"));
    }

    @Test void claimReceiptsPreserveEmptyAndTerminalResults(){
        var claim=new Claim(core.runId(),UUID.randomUUID(),UUID.randomUUID());assertNull(core.claim(claim));
        submit(manifest(task("A")));assertNull(core.claim(claim));
        var other=new Claim(core.runId(),claim.worker_session_id(),UUID.randomUUID());var a=core.claim(other);finish(a);
        assertEquals("TERMINAL_SUCCEEDED",core.claim(other).disposition());
        assertThrows(ApiException.class,()->core.claim(new Claim(core.runId(),UUID.randomUUID(),other.claim_id())));
    }

    @Test void snapshotsAreDetachedAndEventsHaveGapFreePagination(){
        var id=submit(manifest(task("A")));var old=core.snapshot(id);finish(claim());
        assertEquals(JobState.ACCEPTED,old.get("state"));
        long cursor=0;int events=0;boolean more=true;
        while(more){var page=core.events(cursor,2);for(Object e:(List<?>)page.get("events"))assertEquals(++events,((Number)((Map<?,?>)e).get("scheduler_event_seq")).intValue());cursor=((Number)page.get("next_after")).longValue();more=(boolean)page.get("has_more");}
        assertTrue(events>=5);assertThrows(ApiException.class,()->core.events(-1,10));
    }
}
