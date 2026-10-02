package edu.vt.dag;

import java.util.*;
import static edu.vt.dag.Model.*;
import static edu.vt.dag.ApiException.*;

/** Pure structural validation; callers verify immutable source objects outside the scheduler mutex. */
public final class ManifestValidator {
    public static final long MAX_ARTIFACT = 32L * 1024 * 1024;
    public static final int MAX_MANIFEST = 1024 * 1024;
    private ManifestValidator() {}
    public static boolean identifier(String s) { return s != null && s.matches("[A-Za-z0-9][A-Za-z0-9_.-]{0,63}") && !s.contains(".."); }
    public static void artifact(Artifact a) {
        require(a != null && validKey(a.key()), "Invalid artifact key");
        require(a.length() >= 0, "Negative artifact size");
        if (a.length() > MAX_ARTIFACT) throw new ApiException(413,"ARTIFACT_TOO_LARGE","Artifact exceeds 32 MiB");
        require(a.sha256() != null && a.sha256().matches("[0-9a-f]{64}"), "Invalid SHA-256");
        require(a.media_type() != null && a.media_type().matches("[A-Za-z0-9.+-]+/[A-Za-z0-9.+-]+"), "Invalid media type");
    }
    public static boolean validKey(String k) {
        if (k == null || k.length() > 512) return false;
        String[] p = k.split("/",-1);
        try {
            if (p.length == 3 && p[0].equals("inputs")) {
                UUID.fromString(p[1]); return identifier(p[2]);
            }
            if (p.length == 10 && p[0].equals("runs") && p[2].equals("jobs") && p[4].equals("tasks") && p[6].equals("attempts")) {
                // Reserved longer paths are never accepted.
                return false;
            }
            if (p.length == 9 && p[0].equals("runs") && p[2].equals("jobs") && p[4].equals("tasks") && p[6].equals("attempts")) {
                UUID.fromString(p[1]); UUID.fromString(p[3]);
                return identifier(p[5]) && p[7].matches("[1-9][0-9]{0,8}") && identifier(p[8]);
            }
        } catch (IllegalArgumentException ignored) { return false; }
        return false;
    }
    public static void validate(Manifest m) {
        require(m != null && m.schema_version() == 1 && m.job_id() != null, "Manifest version 1 and job UUID required");
        require(m.tasks() != null && !m.tasks().isEmpty(), "Empty DAG");
        if (m.tasks().size() > 128) throw new ApiException(413,"DAG_TOO_LARGE","Maximum 128 tasks");
        var tasks = new TreeMap<String,TaskSpec>();
        int edges = 0;
        for (var t : m.tasks()) {
            require(t != null && identifier(t.task_id()), "Invalid task ID");
            require(tasks.putIfAbsent(t.task_id(), t) == null, "Duplicate task ID");
            require(t.parents() != null && t.inputs() != null && t.outputs() != null && t.parameters() != null, "Task fields required");
            require(new HashSet<>(t.parents()).size() == t.parents().size(), "Duplicate parent");
            require(new HashSet<>(t.outputs()).size() == t.outputs().size() && !t.outputs().isEmpty(), "Invalid output list");
            for (String name : t.outputs()) require(identifier(name), "Invalid output name");
            for (String name : t.inputs().keySet()) require(identifier(name), "Invalid input name");
            edges += t.parents().size(); validateOperation(t);
        }
        if (edges > 512) throw new ApiException(413,"DAG_TOO_LARGE","Maximum 512 edges");
        var indegrees = new HashMap<String,Integer>();
        var children = new HashMap<String,List<String>>();
        for (var t : tasks.values()) {
            indegrees.put(t.task_id(), t.parents().size());
            for (String parent : t.parents()) {
                require(tasks.containsKey(parent) && !parent.equals(t.task_id()), "Unknown parent or self edge");
                children.computeIfAbsent(parent, k -> new ArrayList<>()).add(t.task_id());
            }
            for (Binding b : t.inputs().values()) {
                require(b != null, "Null input binding");
                if (b.source() != null) {
                    require(b.task_id() == null && b.output_name() == null, "Mixed input binding");
                    artifact(b.source()); require(b.source().key().startsWith("inputs/"), "Source must use inputs namespace");
                } else {
                    require(t.parents().contains(b.task_id()), "Input must name declared parent");
                    require(tasks.get(b.task_id()).outputs().contains(b.output_name()), "Unknown parent output");
                }
            }
        }
        var ready = new ArrayDeque<String>();
        indegrees.forEach((id,n) -> { if (n == 0) ready.add(id); });
        int seen = 0;
        while (!ready.isEmpty()) {
            String id=ready.remove(); seen++;
            for (String child:children.getOrDefault(id,List.of())) if (indegrees.merge(child,-1,Integer::sum)==0) ready.add(child);
        }
        require(seen==tasks.size(), "Cycle in DAG");
        require(m.final_outputs()!=null && !m.final_outputs().isEmpty(), "Final output bindings required");
        m.final_outputs().forEach((name,b) -> require(identifier(name) && b!=null && tasks.containsKey(b.task_id()) && tasks.get(b.task_id()).outputs().contains(b.output_name()), "Invalid final binding"));
    }
    private static void validateOperation(TaskSpec t) {
        var p=t.parameters();
        require(p.delay_ms()==null || (p.delay_ms()>=0 && p.delay_ms()<=30000), "delay_ms outside 0..30000");
        require(t.operation()!=null, "Operation required");
        Set<String> ins; String out;
        switch(t.operation()) {
            case "fixture_write" -> {ins=Set.of(); out="value"; require(p.value()!=null,"value required");}
            case "fixture_add", "fixture_multiply" -> {ins=Set.of("value"); out="value"; require(p.amount()!=null,"amount required");}
            case "fixture_sum" -> {ins=t.inputs().keySet(); out="value"; require(!ins.isEmpty(),"Sum needs inputs");}
            case "fixture_format" -> {ins=Set.of("value"); out="text";}
            case "video_inspect" -> {ins=Set.of("video"); out="metadata";}
            case "video_transcode" -> {ins=Set.of("video"); out="video"; require(Objects.equals(p.height(),360)||Objects.equals(p.height(),720),"height must be 360 or 720");}
            case "video_thumbnail" -> {ins=Set.of("video"); out="image";}
            case "fixture_subtitles" -> {ins=Set.of("srt"); out="subtitles";}
            case "video_publish" -> {ins=Set.of("video720","video360","image","subtitles"); out="manifest";}
            default -> throw bad("Unsupported operation");
        }
        require(t.inputs().keySet().equals(ins) && t.outputs().equals(List.of(out)),"Operation input/output names do not match contract");
        require(p.value()==null || t.operation().equals("fixture_write"),"Unexpected value");
        require(p.amount()==null || Set.of("fixture_add","fixture_multiply").contains(t.operation()),"Unexpected amount");
        require(p.height()==null || t.operation().equals("video_transcode"),"Unexpected height");
        require(p.delay_ms()==null || t.operation().startsWith("fixture_"),"delay_ms only for fixture operations");
    }
}
