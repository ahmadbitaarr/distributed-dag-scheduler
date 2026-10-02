package edu.vt.dag;

import java.io.IOException;
import java.net.URI;
import java.net.http.*;
import java.time.Duration;
import java.util.Map;

public final class Transport {
    public final HttpClient client=HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(2)).version(HttpClient.Version.HTTP_1_1).build();
    public HttpResponse<byte[]> request(String method,String url,Object body) throws IOException,InterruptedException {
        var b=HttpRequest.newBuilder(URI.create(url)).timeout(Duration.ofSeconds(5));
        b.method(method,body==null?HttpRequest.BodyPublishers.noBody():HttpRequest.BodyPublishers.ofByteArray(Json.bytes(body)));
        if(body!=null) b.header("Content-Type","application/json");
        return client.send(b.build(),HttpResponse.BodyHandlers.ofByteArray());
    }
    public static void ok(HttpResponse<?> r) {
        if(r.statusCode()<200||r.statusCode()>=300) throw new ApiException(r.statusCode(),"REMOTE_ERROR",r.body() instanceof byte[] b?new String(b):"HTTP "+r.statusCode());
    }
    public static long backoff(int failures) { return switch(Math.min(failures,3)) {case 0->100;case 1->200;case 2->400;default->1000;}; }
}
