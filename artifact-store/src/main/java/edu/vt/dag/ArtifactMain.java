package edu.vt.dag;

import java.io.*;
import java.nio.file.*;
import java.security.*;
import java.util.*;
import java.util.concurrent.*;
import static edu.vt.dag.Model.*;

/** Completed-object index deliberately lives for one service process; files are retained. */
public final class ArtifactMain {
    record Stored(Artifact descriptor,Path file) {}
    public static void main(String[] args) throws Exception {
        start(HttpSupport.envInt("PORT",8081),Path.of(HttpSupport.env("DATA_DIR",".runtime/objects")));
    }
    /** Starts the service; port 0 picks an ephemeral port (tests). */
    public static com.sun.net.httpserver.HttpServer start(int port,Path data) throws IOException {
        Files.createDirectories(data);
        var index=new ConcurrentHashMap<String,Stored>();
        Object[] locks=new Object[64];Arrays.setAll(locks,i->new Object());
        return HttpSupport.serve(port,ex->{
            String path=ex.getRequestURI().getPath(),method=ex.getRequestMethod();
            if(path.equals("/health")||path.equals("/v1/health")) {HttpSupport.method(ex,"GET");HttpSupport.send(ex,200,Map.of("ready",true));return;}
            if(!path.startsWith("/v1/objects/"))throw new ApiException(404,"NOT_FOUND","Unknown endpoint");
            String key=path.substring(12);ApiException.require(ManifestValidator.validKey(key),"Invalid object key");
            if(method.equals("PUT")) {
                long length;try{length=Long.parseLong(ex.getRequestHeaders().getFirst("Content-Length"));}catch(Exception e){throw ApiException.bad("Content-Length required");}
                String hash=ex.getRequestHeaders().getFirst("X-Content-SHA256"),media=ex.getRequestHeaders().getFirst("Content-Type");
                var descriptor=new Artifact(key,length,hash,media);ManifestValidator.artifact(descriptor);
                Path temp=Files.createTempFile(data,"stage-",".tmp");
                try {
                    var digest=MessageDigest.getInstance("SHA-256");long read=0;
                    try(var out=Files.newOutputStream(temp)) {
                        byte[] b=new byte[65536];int n;
                        while((n=ex.getRequestBody().read(b))!=-1){read+=n;if(read>length||read>ManifestValidator.MAX_ARTIFACT)throw ApiException.bad("Length mismatch");digest.update(b,0,n);out.write(b,0,n);}
                    }
                    ApiException.require(read==length && HexFormat.of().formatHex(digest.digest()).equals(hash),"Length/hash mismatch");
                    int status;Artifact response;
                    synchronized(locks[(key.hashCode()&0x7fffffff)%locks.length]) {
                        var old=index.get(key);
                        if(old!=null) {
                            if(!old.descriptor().equals(descriptor))throw ApiException.conflict("Immutable object key already has different bytes or media type");
                            status=200;response=old.descriptor();
                        } else {
                            Path complete=data.resolve("object-"+UUID.randomUUID());Files.move(temp,complete);
                            index.put(key,new Stored(descriptor,complete));status=201;response=descriptor;
                        }
                    }
                    HttpSupport.send(ex,status,response);
                } finally {Files.deleteIfExists(temp);}
            } else if(method.equals("GET")||method.equals("HEAD")) {
                var stored=index.get(key);if(stored==null)throw new ApiException(404,"OBJECT_NOT_FOUND","Object is not published");
                var a=stored.descriptor();ex.getResponseHeaders().set("Content-Type",a.media_type());ex.getResponseHeaders().set("Content-Length",""+a.length());ex.getResponseHeaders().set("X-Content-SHA256",a.sha256());
                if(method.equals("HEAD")){ex.sendResponseHeaders(200,-1);return;}
                ex.sendResponseHeaders(200,a.length()==0?-1:a.length());try(var in=Files.newInputStream(stored.file())){in.transferTo(ex.getResponseBody());}
            } else throw new ApiException(405,"METHOD_NOT_ALLOWED","PUT, HEAD, or GET required");
        });
    }
}
