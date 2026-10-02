package edu.vt.dag;

import java.util.*;
import static edu.vt.dag.Model.*;

/** Mutable records are reachable only during a StateStore command. */
public final class SchedulerState {
    final UUID runId=UUID.randomUUID();
    final Map<UUID,Job> jobs=new LinkedHashMap<>();
    final ArrayDeque<TaskRef> ready=new ArrayDeque<>();
    final Map<UUID,Identity> active=new HashMap<>();
    final Map<UUID,ClaimReceipt> claims=new HashMap<>();
    final List<Map<String,Object>> events=new ArrayList<>();
    final Map<String,Long> counters=new TreeMap<>();
    long readySequence;
    record TaskRef(UUID jobId,String taskId) {}
    record ClaimReceipt(Claim request,Identity identity) {}
    static final class Job {
        final Manifest manifest;
        final Map<String,Task> tasks=new TreeMap<>();
        final long acceptedNs;
        JobState state=JobState.ACCEPTED;
        Long completedNs;
        Job(Manifest m,long ns) {manifest=m;acceptedNs=ns;m.tasks().forEach(t->tasks.put(t.task_id(),new Task(t)));}
    }
    static final class Task {
        final TaskSpec spec;
        final Set<String> satisfied=new TreeSet<>();
        final List<String> children=new ArrayList<>();
        final List<Attempt> attempts=new ArrayList<>();
        TaskState state=TaskState.BLOCKED;
        long readyNs,readySeq;
        Map<String,Artifact> acceptedOutputs;
        Task(TaskSpec spec) {this.spec=spec;}
        Attempt latest() {return attempts.isEmpty()?null:attempts.getLast();}
    }
    static final class Attempt {
        final Identity identity;
        final long readyNs,assignedNs;
        final Map<String,Artifact> inputs;
        long assignmentSeq;
        Long startedNs,finishedNs;
        AttemptState state=AttemptState.ASSIGNED;
        Ack startAck,reportAck;
        Report receipt;
        Attempt(Identity id,long readyNs,long assignedNs,Map<String,Artifact> inputs) {
            identity=id;this.readyNs=readyNs;this.assignedNs=assignedNs;this.inputs=Map.copyOf(inputs);
        }
    }
}
