package edu.vt.dag;

import java.io.*;
import java.net.http.*;
import java.nio.file.*;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.*;
import static edu.vt.dag.Model.*;

public final class WorkerMain {
    private final String scheduler=HttpSupport.env("SCHEDULER_URL","http://localhost:8080");
    private final ArtifactClient artifacts=new ArtifactClient(HttpSupport.env("ARTIFACT_BASE_URL","http://localhost:8081"));
    private final Transport transport=new Transport();
    private final long origin=System.nanoTime();
    private UUID run,session=UUID.randomUUID();
    private long sequence;
    private volatile boolean stopping;
    private static final class RunChanged extends Exception {}
    private synchronized void event(String type,Identity id,Object... pairs) {
        var e=new LinkedHashMap<String,Object>();
        e.put("schema_version",1);e.put("scheduler_run_id",run);e.put("producer","worker");e.put("producer_seq",++sequence);
        e.put("utc_timestamp",Instant.now().toString());e.put("elapsed_ns",System.nanoTime()-origin);e.put("event_type",type);
        e.put("worker_session_id",session);e.put("job_id",id==null?null:id.job_id());e.put("task_id",id==null?null:id.task_id());e.put("attempt_no",id==null?null:id.attempt_no());
        e.put("request_id",id==null?null:id.toString());for(int i=0;i<pairs.length;i+=2)e.put((String)pairs[i],pairs[i+1]);System.out.println(Json.string(e));
    }
    private UUID health()throws IOException,InterruptedException {
        var r=transport.request("GET",scheduler+"/v1/health",null);Transport.ok(r);
        return UUID.fromString(Json.MAPPER.readTree(r.body()).get("scheduler_run_id").asText());
    }
    private void checkRun()throws RunChanged,InterruptedException {
        try{if(!health().equals(run))throw new RunChanged();}catch(IOException|ApiException ignored){}
    }
    private HttpResponse<byte[]> retry(String path,Object body)throws InterruptedException,RunChanged {
        for(int failures=0;;failures++) {
            try{
                var r=transport.request("POST",scheduler+path,body);
                if(!r.headers().firstValue("X-Scheduler-Run-Id").orElse(run.toString()).equals(run.toString()))throw new RunChanged();
                if(r.statusCode()<500){Transport.ok(r);return r;}
            }catch(IOException ignored){}
            checkRun();Thread.sleep(Transport.backoff(failures));
        }
    }
    private Artifact upload(String key,Operations.Product p)throws InterruptedException,RunChanged,IOException {
        for(int failures=0;;failures++) {
            try{return artifacts.put(key,p.file(),p.mediaType());}
            catch(ApiException e){if(e.status<500)throw e;}
            catch(IOException e){if(!Files.exists(p.file()))throw e;}
            checkRun();Thread.sleep(Transport.backoff(failures));
        }
    }
    private void attempt(Assignment a)throws Exception {
        var id=a.identity();var ack=Json.read(retry("/v1/attempts/start",id).body(),Ack.class);
        event("worker_operation_started",id,"ack_scheduler_event_seq",ack.scheduler_event_seq());
        Path dir=Files.createTempDirectory("dag-attempt-");
        var executor=Executors.newSingleThreadExecutor();
        try {
            var future=executor.submit(()->{
                if(Boolean.parseBoolean(HttpSupport.env("ENABLE_TEST_HOOKS","false"))) {
                    if(id.task_id().equals(HttpSupport.env("TEST_GATE_TASK",""))) {
                        event("worker_test_gate_entered",id,"ack_scheduler_event_seq",ack.scheduler_event_seq());
                        while(true)Thread.sleep(1000);
                    }
                    if(id.attempt_no()==1 && id.task_id().equals(HttpSupport.env("TEST_FAIL_FIRST_TASK","")))throw new IOException("Controlled attempt-1 failure");
                }
                return new Operations(artifacts).execute(a,dir);
            });
            Map<String,Operations.Product> products=null;Failure failure=null;
            try{products=future.get(HttpSupport.envInt("OPERATION_TIMEOUT_MS",30000),TimeUnit.MILLISECONDS);}
            catch(TimeoutException e){future.cancel(true);failure=new Failure("OPERATION_TIMEOUT","Local operation exceeded its timeout");}
            catch(ExecutionException e){String message=e.getCause().toString();failure=new Failure("OPERATION_FAILED",message.substring(0,Math.min(2048,message.length())));}
            if(failure!=null) {
                event("worker_operation_failed",id,"error",failure);
                retry("/v1/attempts/report",new Report(id,"FAILURE",Map.of(),failure));
            } else {
                var outputs=new TreeMap<String,Artifact>();
                for(var e:products.entrySet())outputs.put(e.getKey(),upload(a.output_prefix()+e.getKey(),e.getValue()));
                var report=new Report(id,"SUCCESS",outputs,null);
                event("worker_report_sent",id,"report",report);
                retry("/v1/attempts/report",report);
            }
        } finally {
            executor.shutdownNow();
            if(!executor.awaitTermination(5,TimeUnit.SECONDS))throw new IOException("Operation did not stop; worker refuses another attempt");
            try(var paths=Files.walk(dir)){for(Path p:paths.sorted(Comparator.reverseOrder()).toList())Files.deleteIfExists(p);}
        }
    }
    private void loop()throws Exception {
        while(!stopping) {
            try{
                if(run==null){try{run=health();event("worker_session_started",null);}catch(IOException|ApiException e){Thread.sleep(100);continue;}}
                var claim=new Claim(run,session,UUID.randomUUID());
                var r=retry("/v1/work/claim",claim);
                if(r.statusCode()==204){event("work_empty",null,"request_id",claim.claim_id());Thread.sleep(HttpSupport.envInt("POLL_INTERVAL_MS",100));continue;}
                var a=Json.read(r.body(),Assignment.class);
                if(a.disposition().equals("EXECUTE"))attempt(a);
            }catch(RunChanged e){event("scheduler_run_changed",null);run=null;session=UUID.randomUUID();}
            catch(ApiException e){event("attempt_rejected",null,"status",e.status,"message",e.getMessage());throw e;}
        }
    }
    public static void main(String[] args)throws Exception {
        var worker=new WorkerMain();var thread=Thread.currentThread();
        Runtime.getRuntime().addShutdownHook(new Thread(()->{worker.stopping=true;thread.interrupt();}));
        // Only the Hokea role wrapper enables this readiness-only port. No task-control endpoint.
        if(System.getenv("HOKEA_HEALTH_PORT")!=null)HttpSupport.serve(HttpSupport.envInt("HOKEA_HEALTH_PORT",8000),ex->{HttpSupport.method(ex,"GET");if(!Set.of("/health","/v1/health").contains(ex.getRequestURI().getPath()))throw new ApiException(404,"NOT_FOUND","Health only");HttpSupport.send(ex,200,Map.of("ready",true));});
        try{worker.loop();}catch(InterruptedException e){if(!worker.stopping)throw e;}
    }
}
