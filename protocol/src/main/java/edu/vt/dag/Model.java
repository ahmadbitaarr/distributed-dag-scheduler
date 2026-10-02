package edu.vt.dag;

import java.util.*;

/** Version 1 wire records. Immutable collections also define semantic replay equality. */
public final class Model {
    private Model() {}
    public enum TaskState { BLOCKED, READY, ASSIGNED, RUNNING, SUCCEEDED }
    public enum AttemptState { ASSIGNED, RUNNING, SUCCEEDED, FAILED }
    public enum JobState { ACCEPTED, RUNNING, SUCCEEDED }
    public record Artifact(String key, long length, String sha256, String media_type) {}
    public record Binding(Artifact source, String task_id, String output_name) {}
    public record OutputBinding(String task_id, String output_name) {}
    public record Parameters(Long value, Long amount, Integer delay_ms, Integer height) {}
    public record TaskSpec(String task_id, String operation, Parameters parameters,
                           List<String> parents, Map<String, Binding> inputs, List<String> outputs) {
        public TaskSpec {
            parents = sorted(parents);
            inputs = frozen(inputs);
            outputs = sorted(outputs);
        }
    }
    public record Manifest(int schema_version, UUID job_id, List<TaskSpec> tasks,
                           Map<String, OutputBinding> final_outputs) {
        public Manifest {
            if (tasks != null) {
                var copy = new ArrayList<>(tasks);
                copy.sort(Comparator.comparing(TaskSpec::task_id, Comparator.nullsFirst(String::compareTo)));
                tasks = List.copyOf(copy);
            }
            final_outputs = frozen(final_outputs);
        }
    }
    public record Submission(UUID scheduler_run_id, Manifest manifest) {}
    public record Claim(UUID scheduler_run_id, UUID worker_session_id, UUID claim_id) {}
    public record Identity(UUID scheduler_run_id, UUID job_id, String task_id, int attempt_no,
                           UUID worker_session_id) {}
    public record Failure(String code, String message) {}
    public record Report(Identity identity, String outcome, Map<String, Artifact> outputs, Failure error) {
        public Report { outputs = frozen(outputs); }
    }
    public record Ack(UUID scheduler_run_id, long scheduler_event_seq, String disposition) {}
    public record Assignment(UUID scheduler_run_id, Identity identity, TaskSpec task,
                             Map<String, Artifact> inputs, String output_prefix,
                             long scheduler_event_seq, String disposition) {}
    public static <T> Map<String,T> frozen(Map<String,T> values) {
        return values == null ? null : Collections.unmodifiableMap(new TreeMap<>(values));
    }
    private static List<String> sorted(List<String> values) {
        if (values == null) return null;
        var copy = new ArrayList<>(values);
        copy.sort(Comparator.nullsFirst(String::compareTo));
        return List.copyOf(copy);
    }
    public static String prefix(Identity id) {
        return "runs/" + id.scheduler_run_id() + "/jobs/" + id.job_id() + "/tasks/" +
            id.task_id() + "/attempts/" + id.attempt_no() + "/";
    }
}
