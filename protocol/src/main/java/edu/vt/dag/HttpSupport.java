package edu.vt.dag;

import com.sun.net.httpserver.*;
import java.io.*;
import java.net.*;
import java.util.*;
import java.util.concurrent.*;

/** Bounded HTTP plumbing shared by the two services. Domain commands perform no I/O. */
public final class HttpSupport {
    private HttpSupport() {}
    @FunctionalInterface public interface Handler { void handle(HttpExchange ex) throws Exception; }
    public static HttpServer serve(int port, Handler handler) throws IOException {
        var server=HttpServer.create(new InetSocketAddress("0.0.0.0",port),128);
        var pool=new ThreadPoolExecutor(16,16,0,TimeUnit.SECONDS,new ArrayBlockingQueue<>(128),new ThreadPoolExecutor.CallerRunsPolicy());
        var slots=new Semaphore(16);
        server.setExecutor(pool);
        server.createContext("/", ex -> {
            boolean acquired=slots.tryAcquire();
            try {
                if (!acquired) throw new ApiException(503,"OVERLOADED","Handler capacity exhausted");
                handler.handle(ex);
            } catch(ApiException e) { send(ex,e.status,Map.of("error",Map.of("code",e.code,"message",e.getMessage()))); }
            catch(Exception e) {
                System.err.println(Json.string(Map.of("event_type","server_error","message",e.toString())));
                send(ex,503,Map.of("error",Map.of("code","SERVICE_UNAVAILABLE","message","Service operation failed")));
            } finally { if(acquired) slots.release(); ex.close(); }
        });
        Runtime.getRuntime().addShutdownHook(new Thread(() -> { server.stop(1); pool.shutdownNow(); }));
        server.start(); return server;
    }
    public static <T> T body(HttpExchange ex,Class<T> type) throws IOException {
        byte[] b=ex.getRequestBody().readNBytes(ManifestValidator.MAX_MANIFEST+1);
        if(b.length>ManifestValidator.MAX_MANIFEST) throw new ApiException(413,"MANIFEST_TOO_LARGE","JSON exceeds 1 MiB");
        return Json.read(b,type);
    }
    public static void send(HttpExchange ex,int status,Object value) throws IOException {
        if(status==204) { ex.sendResponseHeaders(status,-1); return; }
        byte[] b=Json.bytes(value); ex.getResponseHeaders().set("Content-Type","application/json");
        if(ex.getRequestMethod().equals("HEAD")) {ex.getResponseHeaders().set("Content-Length",""+b.length);ex.sendResponseHeaders(status,-1);return;}
        ex.sendResponseHeaders(status,b.length); ex.getResponseBody().write(b);
    }
    public static void method(HttpExchange ex,String expected) {
        if(!ex.getRequestMethod().equals(expected)) throw new ApiException(405,"METHOD_NOT_ALLOWED",expected+" required");
    }
    public static int envInt(String name,int fallback) { return Integer.parseInt(System.getenv().getOrDefault(name,""+fallback)); }
    public static String env(String name,String fallback) { return System.getenv().getOrDefault(name,fallback); }
}
