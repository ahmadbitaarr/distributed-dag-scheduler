package edu.vt.dag;

import java.nio.file.*;
import java.util.*;
import static edu.vt.dag.Model.*;

/** Small Java client. upload FILE [NAME], submit MANIFEST, status JOB_ID, fetch KEY DEST. */
public final class ClientMain {
    public static void main(String[] args)throws Exception {
        if(args.length==0)throw new IllegalArgumentException("upload FILE [NAME] | submit MANIFEST | status JOB_ID | fetch KEY DEST");
        var transport=new Transport();String scheduler=HttpSupport.env("SCHEDULER_URL","http://localhost:8080");
        var artifacts=new ArtifactClient(HttpSupport.env("ARTIFACT_BASE_URL","http://localhost:8081"));
        switch(args[0]) {
            case "upload" -> {
                Path file=Path.of(args[1]);String name=args.length>2?args[2]:file.getFileName().toString();
                String media=name.endsWith(".mp4")?"video/mp4":name.endsWith(".srt")?"application/x-subrip":"application/octet-stream";
                String key="inputs/"+UUID.randomUUID()+"/"+name;
                for(int tries=0;;tries++)try{System.out.println(Json.string(artifacts.put(key,file,media)));break;}catch(java.io.IOException e){Thread.sleep(Transport.backoff(tries));}
            }
            case "submit" -> {
                var m=Json.read(Files.readAllBytes(Path.of(args[1])),Manifest.class);ManifestValidator.validate(m);
                var h=transport.request("GET",scheduler+"/v1/health",null);Transport.ok(h);
                var run=UUID.fromString(Json.MAPPER.readTree(h.body()).get("scheduler_run_id").asText());var submission=new Submission(run,m);
                for(int tries=0;;tries++){
                    try{var r=transport.request("POST",scheduler+"/v1/jobs",submission);if(r.statusCode()>=500){Thread.sleep(Transport.backoff(tries));continue;}Transport.ok(r);System.out.println(new String(r.body()));break;}
                    catch(java.io.IOException e){Thread.sleep(Transport.backoff(tries));}
                }
            }
            case "status" -> {var r=transport.request("GET",scheduler+"/v1/jobs/"+args[1],null);Transport.ok(r);System.out.println(new String(r.body()));}
            case "fetch" -> {artifacts.get(artifacts.head(args[1]),Path.of(args[2]));System.out.println(args[2]);}
            default -> throw new IllegalArgumentException("Unknown command");
        }
    }
}
