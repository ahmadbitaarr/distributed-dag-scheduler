package edu.vt.dag;

import java.util.*;
import java.util.concurrent.*;
import static edu.vt.dag.Model.*;

public final class SchedulerMain {
    public static void main(String[] args) throws Exception {
        var core=new SchedulerCore();var artifacts=new ArtifactClient(HttpSupport.env("ARTIFACT_BASE_URL","http://localhost:8081"));
        HttpSupport.serve(HttpSupport.envInt("PORT",8080),ex->{
            ex.getResponseHeaders().set("X-Scheduler-Run-Id",core.runId().toString());
            String path=ex.getRequestURI().getPath();
            switch(path) {
                case "/health", "/v1/health" -> {HttpSupport.method(ex,"GET");HttpSupport.send(ex,200,Map.of("ready",true,"scheduler_run_id",core.runId()));}
                case "/v1/jobs" -> {
                    HttpSupport.method(ex,"POST");var r=HttpSupport.body(ex,Submission.class);ApiException.require(r!=null,"Submission required");ManifestValidator.validate(r.manifest());
                    var result=core.submissionReplay(r);
                    if(result==null) {
                        for(var t:r.manifest().tasks())for(var b:t.inputs().values())if(b.source()!=null)artifacts.verify(b.source());
                        result=core.submit(r);
                    }
                    HttpSupport.send(ex,result.status(),result.body());
                }
                case "/v1/work/claim" -> {HttpSupport.method(ex,"POST");var a=core.claim(HttpSupport.body(ex,Claim.class));HttpSupport.send(ex,a==null?204:200,a);}
                case "/v1/attempts/start" -> {HttpSupport.method(ex,"POST");var id=HttpSupport.body(ex,Identity.class);try{HttpSupport.send(ex,200,core.start(id));}catch(ApiException e){core.rejected(id,e.code);throw e;}}
                case "/v1/attempts/report" -> {
                    HttpSupport.method(ex,"POST");var r=HttpSupport.body(ex,Report.class);
                    try {
                        var ack=core.prepareReport(r);
                        if(ack==null) {if(r.outcome().equals("SUCCESS"))for(var a:r.outputs().values())artifacts.verify(a);ack=core.report(r);}
                        HttpSupport.send(ex,200,ack);
                    } catch(ApiException e){core.rejected(r==null?null:r.identity(),e.code);throw e;}
                }
                case "/v1/events" -> {
                    HttpSupport.method(ex,"GET");long after=0;int limit=1000;
                    try {String q=ex.getRequestURI().getQuery();if(q!=null)for(String part:q.split("&")){var kv=part.split("=",2);if(kv.length!=2)throw new NumberFormatException();switch(kv[0]){case "after"->after=Long.parseLong(kv[1]);case "limit"->limit=Integer.parseInt(kv[1]);default->throw ApiException.bad("Unknown query field");}}}
                    catch(NumberFormatException e){throw ApiException.bad("Invalid cursor");}
                    HttpSupport.send(ex,200,core.events(after,limit));
                }
                case "/v1/metrics" -> {HttpSupport.method(ex,"GET");HttpSupport.send(ex,200,core.metrics());}
                default -> {
                    if(path.startsWith("/v1/jobs/")) {
                        HttpSupport.method(ex,"GET");UUID id;try{id=UUID.fromString(path.substring(9));}catch(IllegalArgumentException e){throw ApiException.bad("Invalid job UUID");}
                        HttpSupport.send(ex,200,core.snapshot(id));
                    } else throw new ApiException(404,"NOT_FOUND","Unknown endpoint");
                }
            }
        });
        var exporter=Executors.newSingleThreadScheduledExecutor();
        long[] cursor={0};
        Runnable drain=()->{boolean more;do{var page=core.events(cursor[0],1000);for(Object event:(List<?>)page.get("events"))System.out.println(Json.string(event));cursor[0]=((Number)page.get("next_after")).longValue();more=(boolean)page.get("has_more");}while(more);};
        exporter.scheduleWithFixedDelay(drain,0,50,TimeUnit.MILLISECONDS);
        Runtime.getRuntime().addShutdownHook(new Thread(()->{exporter.shutdown();try{exporter.awaitTermination(1,TimeUnit.SECONDS);}catch(InterruptedException e){Thread.currentThread().interrupt();}drain.run();}));
    }
}
