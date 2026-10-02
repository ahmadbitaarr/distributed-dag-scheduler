package edu.vt.dag;

import java.time.Instant;
import java.util.*;
import java.util.function.LongSupplier;
import static edu.vt.dag.Model.*;
import static edu.vt.dag.SchedulerState.*;

/** Transport-independent state machine. This class intentionally has no recovery timer. */
public final class SchedulerCore {
    private final StateStore store;
    private final LongSupplier clock;
    private final long origin;
    public SchedulerCore(StateStore store,LongSupplier clock) {this.store=store;this.clock=clock;origin=clock.getAsLong();}
    public SchedulerCore() {this(new MemoryStateStore(),System::nanoTime);}
    long now() {return clock.getAsLong()-origin;}
    public UUID runId() {return store.command(s->s.runId);}
    public static Map<String,Object> map(Object... pairs) {
        var m=new LinkedHashMap<String,Object>();
        for(int i=0;i<pairs.length;i+=2) m.put((String)pairs[i],pairs[i+1]);
        return Collections.unmodifiableMap(m);
    }
    private void run(SchedulerState s,UUID run) {ApiException.require(run!=null,"scheduler_run_id required");if(!s.runId.equals(run)) throw new ApiException(409,"STALE_RUN","Scheduler run changed");}
    private void count(SchedulerState s,String key) {s.counters.merge(key,1L,Long::sum);}
    private long event(SchedulerState s,String type,String request,Identity id,UUID job,String task,Object... detail) {
        long seq=s.events.size()+1L;
        var fields=new LinkedHashMap<>(map("schema_version",1,"scheduler_run_id",s.runId,"event_type",type,
            "producer","scheduler","producer_seq",seq,"scheduler_event_seq",seq,"utc_timestamp",Instant.now().toString(),
            "elapsed_ns",now(),"request_id",request,"job_id",id==null?job:id.job_id(),"task_id",id==null?task:id.task_id(),
            "attempt_no",id==null?null:id.attempt_no(),"worker_session_id",id==null?null:id.worker_session_id()));
        fields.putAll(map(detail)); s.events.add(Collections.unmodifiableMap(fields)); return seq;
    }
    private void ready(SchedulerState s,UUID job,Task t,String request,TaskState old) {
        t.state=TaskState.READY;t.readyNs=now();t.readySeq=++s.readySequence;
        s.ready.add(new TaskRef(job,t.spec.task_id()));
        event(s,"task_ready",request,null,job,t.spec.task_id(),"old_state",old,"new_state",t.state,"ready_seq",t.readySeq,"satisfied_parents",List.copyOf(t.satisfied));
    }
    public record SubmissionResult(int status,Map<String,Object> body) {}
    public SubmissionResult submissionReplay(Submission r) {
        return store.command(s->{run(s,r.scheduler_run_id());var j=s.jobs.get(r.manifest().job_id());
            if(j==null)return null;
            if(!j.manifest.equals(r.manifest()))throw ApiException.conflict("Job ID already has a different manifest");
            return new SubmissionResult(200,map("scheduler_run_id",s.runId,"job_id",j.manifest.job_id(),"state",j.state,"scheduler_event_seq",s.events.size()));});
    }
    public SubmissionResult submit(Submission r) {
        return store.command(s->{
            run(s,r.scheduler_run_id());ManifestValidator.validate(r.manifest());
            var existing=s.jobs.get(r.manifest().job_id());
            if(existing!=null) {
                if(!existing.manifest.equals(r.manifest()))throw ApiException.conflict("Job ID already has a different manifest");
                return new SubmissionResult(200,map("scheduler_run_id",s.runId,"job_id",r.manifest().job_id(),"state",existing.state,"scheduler_event_seq",s.events.size()));
            }
            var j=new Job(r.manifest(),now()); UUID job=r.manifest().job_id();String request=job.toString();
            for(var t:j.tasks.values())for(String p:t.spec.parents())j.tasks.get(p).children.add(t.spec.task_id());
            s.jobs.put(job,j);count(s,"accepted_jobs");
            event(s,"job_submitted",request,null,job,null,"state",j.state);
            for(var t:j.tasks.values())if(t.spec.parents().isEmpty())ready(s,job,t,request,null);
            return new SubmissionResult(201,map("scheduler_run_id",s.runId,"job_id",job,"state",j.state,"scheduler_event_seq",s.events.size()));
        });
    }
    private Task task(SchedulerState s,Identity id) {
        ManifestValidator.identity(id);run(s,id.scheduler_run_id());
        var j=s.jobs.get(id.job_id());
        if(j==null || !j.tasks.containsKey(id.task_id()))throw ApiException.conflict("Unknown task in this run");
        return j.tasks.get(id.task_id());
    }
    private Attempt attempt(SchedulerState s,Identity id) {
        var t=task(s,id);
        if(id.attempt_no()>t.attempts.size())throw ApiException.conflict("Unknown attempt");
        var a=t.attempts.get(id.attempt_no()-1);
        if(!a.identity.equals(id))throw ApiException.conflict("Attempt owner mismatch");
        return a;
    }
    private void current(SchedulerState s,Task t,Attempt a) {
        if(t.latest()!=a || !a.identity.equals(s.active.get(a.identity.worker_session_id())) ||
          !(t.state==TaskState.ASSIGNED||t.state==TaskState.RUNNING)) throw ApiException.conflict("Stale or terminal attempt");
    }
    private Assignment assignment(SchedulerState s,Identity id) {
        var t=task(s,id);var a=attempt(s,id);
        boolean terminal=a.state==AttemptState.SUCCEEDED||a.state==AttemptState.FAILED;
        return new Assignment(s.runId,id,t.spec,a.inputs,Model.prefix(id),a.assignmentSeq,terminal?"TERMINAL_"+a.state:"EXECUTE");
    }
    public Assignment claim(Claim r) {
        return store.command(s->{
            ManifestValidator.claim(r);run(s,r.scheduler_run_id());
            var receipt=s.claims.get(r.claim_id());
            if(receipt!=null) {
                if(!receipt.request().equals(r))throw ApiException.conflict("Claim ID reused with different identity");
                return receipt.identity()==null?null:assignment(s,receipt.identity());
            }
            String req=r.claim_id().toString();
            event(s,"work_claim",req,null,null,null,"worker_session_id",r.worker_session_id());
            Identity id=s.active.get(r.worker_session_id());
            if(id==null && !s.ready.isEmpty()) {
                var ref=s.ready.remove(); var j=s.jobs.get(ref.jobId());var t=j.tasks.get(ref.taskId());
                if(t.state!=TaskState.READY)throw new IllegalStateException("Non-ready FIFO entry");
                id=new Identity(s.runId,ref.jobId(),ref.taskId(),t.attempts.size()+1,r.worker_session_id());
                var inputs=new TreeMap<String,Artifact>();
                for(var e:t.spec.inputs().entrySet()) {var b=e.getValue();inputs.put(e.getKey(),b.source()!=null?b.source():j.tasks.get(b.task_id()).acceptedOutputs.get(b.output_name()));}
                var a=new Attempt(id,t.readyNs,now(),inputs);t.attempts.add(a);t.state=TaskState.ASSIGNED;
                s.active.put(r.worker_session_id(),id);j.state=JobState.RUNNING;
                a.assignmentSeq=event(s,"task_assigned",req,id,null,null,"old_state",TaskState.READY,"new_state",t.state,"ready_seq",t.readySeq,"ready_elapsed_ns",a.readyNs,"assigned_elapsed_ns",a.assignedNs);
                if(id.attempt_no()>1) {count(s,"retries_assigned");event(s,"task_retried",req,id,null,null,"previous_attempt_no",id.attempt_no()-1);}
            }
            s.claims.put(r.claim_id(),new ClaimReceipt(r,id));
            if(id==null) {event(s,"work_empty",req,null,null,null,"worker_session_id",r.worker_session_id());return null;}
            return assignment(s,id);
        });
    }
    public Ack start(Identity id) {
        return store.command(s->{
            var t=task(s,id);var a=attempt(s,id);
            if(a.startAck!=null)return a.startAck;
            current(s,t,a);if(t.state!=TaskState.ASSIGNED)throw ApiException.conflict("Start requires ASSIGNED");
            a.state=AttemptState.RUNNING;t.state=TaskState.RUNNING;a.startedNs=now();
            long seq=event(s,"task_started","start:"+id,id,null,null,"old_state",TaskState.ASSIGNED,"new_state",t.state);
            return a.startAck=new Ack(s.runId,seq,"ACCEPTED");
        });
    }
    private void validateReport(SchedulerState s,Report r) {
        ApiException.require(r!=null && r.outputs()!=null,"Report and outputs required");
        var t=task(s,r.identity());var a=attempt(s,r.identity());
        ApiException.require(r.outcome()!=null && Set.of("SUCCESS","FAILURE").contains(r.outcome()),"Outcome must be SUCCESS or FAILURE");
        if(a.receipt!=null) {
            if(!a.receipt.equals(r))throw ApiException.conflict("Conflicting report for a terminal attempt");
            return;
        }
        current(s,t,a);
        if(r.outcome().equals("SUCCESS")) {
            if(t.state!=TaskState.RUNNING)throw ApiException.conflict("Success requires RUNNING");
            ApiException.require(r.error()==null && r.outputs().keySet().equals(new HashSet<>(t.spec.outputs())),"Wrong success outputs/error");
            r.outputs().forEach((name,output)->{ManifestValidator.artifact(output);ApiException.require(output.key().equals(Model.prefix(r.identity())+name),"Output outside its attempt namespace");});
        } else {
            ApiException.require(r.outputs().isEmpty() && r.error()!=null && ManifestValidator.identifier(r.error().code()) &&
                r.error().message()!=null && r.error().message().length()<=2048,"Failure needs a bounded structured error and no outputs");
        }
    }
    /** Return cached receipt without touching storage; otherwise validate before external HEAD checks. */
    public Ack prepareReport(Report r) {
        return store.command(s->{validateReport(s,r);var a=attempt(s,r.identity());
            if(a.receipt==null)return null;return duplicate(s,a);});
    }
    private Ack duplicate(SchedulerState s,Attempt a) {
        count(s,"duplicate_reports");event(s,"completion_duplicate","report:"+a.identity,a.identity,null,null,"outcome",a.receipt.outcome(),"receipt_event_seq",a.reportAck.scheduler_event_seq());return a.reportAck;
    }
    public Ack report(Report r) {
        return store.command(s->{
            validateReport(s,r);var id=r.identity();var t=task(s,id);var a=attempt(s,id);
            if(a.receipt!=null)return duplicate(s,a);
            var j=s.jobs.get(id.job_id());String request="report:"+id;TaskState old=t.state;
            a.receipt=r;a.finishedNs=now();s.active.remove(id.worker_session_id());
            long seq;
            if(r.outcome().equals("FAILURE")) {
                a.state=AttemptState.FAILED;count(s,"explicit_failed_attempts");
                seq=event(s,"task_failed",request,id,null,null,"old_state",old,"new_state",TaskState.READY,"error",r.error(),"report",r);
                ready(s,id.job_id(),t,request,old);
            } else {
                a.state=AttemptState.SUCCEEDED;t.state=TaskState.SUCCEEDED;t.acceptedOutputs=r.outputs();count(s,"accepted_logical_successes");
                seq=event(s,"task_succeeded",request,id,null,null,"old_state",old,"new_state",t.state,"outputs",t.acceptedOutputs,"report",r);
                for(String childId:t.children) {
                    var child=j.tasks.get(childId);
                    if(child.satisfied.add(id.task_id()))event(s,"dependency_satisfied",request,null,id.job_id(),childId,"parent_id",id.task_id(),"parent_success_event_seq",seq);
                    if(child.state==TaskState.BLOCKED && child.satisfied.size()==child.spec.parents().size())ready(s,id.job_id(),child,request,TaskState.BLOCKED);
                }
                if(j.tasks.values().stream().allMatch(x->x.state==TaskState.SUCCEEDED)) {
                    j.state=JobState.SUCCEEDED;j.completedNs=now();event(s,"job_completed",request,null,id.job_id(),null,"state",j.state,"accepted_elapsed_ns",j.acceptedNs,"completed_elapsed_ns",j.completedNs);
                }
            }
            return a.reportAck=new Ack(s.runId,seq,"ACCEPTED");
        });
    }
    public void rejected(Identity id,String code) {
        store.command(s->{count(s,"rejected_reports");event(s,"report_rejected",null,id,null,null,"error_code",code);return null;});
    }
    public Map<String,Object> snapshot(UUID jobId) {
        return store.command(s->{
            var j=s.jobs.get(jobId);if(j==null)throw new ApiException(404,"JOB_NOT_FOUND","Unknown job in current run");
            var tasks=new TreeMap<String,Object>();var counts=new TreeMap<String,Long>();
            for(var t:j.tasks.values()) {
                counts.merge(t.state.name(),1L,Long::sum);
                var attempts=t.attempts.stream().map(a->map("identity",a.identity,"state",a.state,"ready_elapsed_ns",a.readyNs,
                    "assigned_elapsed_ns",a.assignedNs,"started_elapsed_ns",a.startedNs,"finished_elapsed_ns",a.finishedNs,
                    "start_receipt",a.startAck,"report_receipt",a.receipt,"report_ack",a.reportAck)).toList();
                tasks.put(t.spec.task_id(),map("state",t.state,"parents",t.spec.parents(),"satisfied_parents",List.copyOf(t.satisfied),
                    "ready_seq",t.readySeq,"owner",t.state==TaskState.ASSIGNED||t.state==TaskState.RUNNING?t.latest().identity.worker_session_id():null,
                    "attempt_no",t.attempts.size(),"attempts",attempts,"outputs",t.acceptedOutputs));
            }
            var outputs=new TreeMap<String,Artifact>();
            if(j.state==JobState.SUCCEEDED)j.manifest.final_outputs().forEach((name,b)->outputs.put(name,j.tasks.get(b.task_id()).acceptedOutputs.get(b.output_name())));
            return map("scheduler_run_id",s.runId,"job_id",jobId,"state",j.state,"accepted_elapsed_ns",j.acceptedNs,"completed_elapsed_ns",j.completedNs,
                "duration_ns",j.completedNs==null?null:j.completedNs-j.acceptedNs,"tasks",tasks,"counts",counts,"outputs",outputs,"snapshot_event_seq",s.events.size());
        });
    }
    public Map<String,Object> events(long after,int limit) {
        ApiException.require(after>=0 && limit>=1 && limit<=1000,"Invalid event cursor or limit");
        return store.command(s->{int start=(int)Math.min(after,s.events.size()),end=Math.min(start+limit,s.events.size());
            return map("scheduler_run_id",s.runId,"events",List.copyOf(s.events.subList(start,end)),"next_after",end,"has_more",end<s.events.size());});
    }
    public Map<String,Object> metrics() {
        return store.command(s->{
            var gauges=new TreeMap<String,Long>();for(var state:TaskState.values())gauges.put(state.name(),0L);
            var jobs=new ArrayList<Long>();var latency=new ArrayList<Long>();
            for(var j:s.jobs.values()) {
                if(j.completedNs!=null)jobs.add(j.completedNs-j.acceptedNs);
                for(var t:j.tasks.values()){gauges.merge(t.state.name(),1L,Long::sum);for(var a:t.attempts)latency.add(a.assignedNs-a.readyNs);}
            }
            var counters=new TreeMap<String,Long>();for(String k:List.of("accepted_jobs","accepted_logical_successes","explicit_failed_attempts","retries_assigned","duplicate_reports","rejected_reports"))counters.put(k,s.counters.getOrDefault(k,0L));
            return map("scheduler_run_id",s.runId,"scheduler_event_seq",s.events.size(),"counters",counters,"tasks_by_state",gauges,"ready_queue_length",s.ready.size(),"active_attempts",s.active.size(),"job_duration_ns",summary(jobs),"scheduling_latency_ns",summary(latency));
        });
    }
    private Map<String,Object> summary(List<Long> values) {
        values.sort(Long::compare);int n=values.size();
        return map("count",n,"p50",n==0?null:values.get((int)Math.ceil(n*.50)-1),"p95",n==0?null:values.get((int)Math.ceil(n*.95)-1));
    }
}
