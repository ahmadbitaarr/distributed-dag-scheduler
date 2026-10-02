package edu.vt.dag;

import java.io.*;
import java.net.*;
import java.net.http.*;
import java.nio.file.*;
import java.security.*;
import java.time.Duration;
import java.util.*;
import static edu.vt.dag.Model.*;

public final class ArtifactClient {
    private final String base;
    private final Transport transport=new Transport();
    public ArtifactClient(String base) { this.base=base.replaceAll("/$",""); }
    public static String sha256(Path path) throws IOException {
        try {
            var digest=MessageDigest.getInstance("SHA-256");
            try(var in=Files.newInputStream(path)) { byte[] b=new byte[65536]; int n; while((n=in.read(b))!=-1) digest.update(b,0,n); }
            return HexFormat.of().formatHex(digest.digest());
        } catch(NoSuchAlgorithmException e) { throw new IllegalStateException(e); }
    }
    public void verify(Artifact a) {
        ManifestValidator.artifact(a);
        try {
            var r=transport.request("HEAD",base+"/v1/objects/"+a.key(),null);
            if(r.statusCode()==404) throw ApiException.bad("Artifact not published: "+a.key());
            if(r.statusCode()!=200) throw new ApiException(503,"ARTIFACT_UNAVAILABLE","Artifact store unavailable");
            if(!r.headers().firstValue("X-Content-SHA256").orElse("").equals(a.sha256()) ||
               r.headers().firstValueAsLong("Content-Length").orElse(-1)!=a.length() ||
               !r.headers().firstValue("Content-Type").orElse("").equals(a.media_type())) throw ApiException.bad("Artifact descriptor mismatch");
        } catch(IOException e) { throw new ApiException(503,"ARTIFACT_UNAVAILABLE",e.toString()); }
        catch(InterruptedException e) { Thread.currentThread().interrupt(); throw new ApiException(503,"INTERRUPTED","Interrupted"); }
    }
    public Artifact put(String key,Path file,String media) throws IOException,InterruptedException {
        var a=new Artifact(key,Files.size(file),sha256(file),media); ManifestValidator.artifact(a);
        var req=HttpRequest.newBuilder(URI.create(base+"/v1/objects/"+key)).timeout(Duration.ofSeconds(5))
            .header("X-Content-SHA256",a.sha256()).header("Content-Type",media).PUT(HttpRequest.BodyPublishers.ofFile(file)).build();
        var r=transport.client.send(req,HttpResponse.BodyHandlers.ofByteArray()); Transport.ok(r);
        return Json.read(r.body(),Artifact.class);
    }
    public Path get(Artifact a,Path target) throws IOException,InterruptedException {
        ManifestValidator.artifact(a);
        var r=transport.client.send(HttpRequest.newBuilder(URI.create(base+"/v1/objects/"+a.key())).timeout(Duration.ofSeconds(5)).GET().build(),HttpResponse.BodyHandlers.ofFile(target));
        Transport.ok(r);
        if(Files.size(target)!=a.length() || !sha256(target).equals(a.sha256())) { Files.deleteIfExists(target); throw new IOException("Artifact integrity mismatch"); }
        return target;
    }
    public Artifact head(String key) throws IOException,InterruptedException {
        var r=transport.request("HEAD",base+"/v1/objects/"+key,null); Transport.ok(r);
        return new Artifact(key,r.headers().firstValueAsLong("Content-Length").orElseThrow(),r.headers().firstValue("X-Content-SHA256").orElseThrow(),r.headers().firstValue("Content-Type").orElseThrow());
    }
}
