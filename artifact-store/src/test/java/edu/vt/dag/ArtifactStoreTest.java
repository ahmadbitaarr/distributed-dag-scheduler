package edu.vt.dag;

import com.sun.net.httpserver.HttpServer;
import java.io.*;
import java.net.*;
import java.net.http.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.*;
import java.util.concurrent.*;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.io.TempDir;
import static org.junit.jupiter.api.Assertions.*;

/** Real HTTP service on an ephemeral port: publication, visibility, integrity and immutability (architecture §§6, 11). */
class ArtifactStoreTest {
    @TempDir Path data;
    HttpServer server;
    String base;
    final HttpClient http = HttpClient.newBuilder().version(HttpClient.Version.HTTP_1_1).build();
    static final String KEY = "inputs/0b7e5c2a-1d3f-4a6b-9c8d-7e6f5a4b3c2d/clip.bin";

    @BeforeEach void start() throws IOException {
        server = ArtifactMain.start(0, data);
        base = "http://127.0.0.1:" + server.getAddress().getPort() + "/v1/objects/";
    }
    @AfterEach void stop() { server.stop(0); }

    static String sha(byte[] b) throws Exception { return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(b)); }
    HttpResponse<String> put(String key, byte[] body, String hash, String media) throws Exception {
        var b = HttpRequest.newBuilder(URI.create(base + key)).PUT(HttpRequest.BodyPublishers.ofByteArray(body));
        if (hash != null) b.header("X-Content-SHA256", hash);
        if (media != null) b.header("Content-Type", media);
        return http.send(b.build(), HttpResponse.BodyHandlers.ofString());
    }
    HttpResponse<byte[]> get(String key, String method) throws Exception {
        return http.send(HttpRequest.newBuilder(URI.create(base + key)).method(method, HttpRequest.BodyPublishers.noBody()).build(),
            HttpResponse.BodyHandlers.ofByteArray());
    }
    List<Path> files(String glob) throws IOException {
        try (var s = Files.newDirectoryStream(data, glob)) { var l = new ArrayList<Path>(); s.forEach(l::add); return l; }
    }

    @Test void publishHeadGetAndIdenticalReplay() throws Exception {
        byte[] bytes = "hello artifact".getBytes(StandardCharsets.UTF_8);
        var r = put(KEY, bytes, sha(bytes), "application/octet-stream");
        assertEquals(201, r.statusCode());
        var descriptor = Json.read(r.body().getBytes(), Model.Artifact.class);
        assertEquals(new Model.Artifact(KEY, bytes.length, sha(bytes), "application/octet-stream"), descriptor);
        var head = get(KEY, "HEAD");
        assertEquals(200, head.statusCode());
        assertEquals(sha(bytes), head.headers().firstValue("X-Content-SHA256").orElseThrow());
        assertEquals(bytes.length, head.headers().firstValueAsLong("Content-Length").orElseThrow());
        assertArrayEquals(bytes, get(KEY, "GET").body());
        assertEquals(200, put(KEY, bytes, sha(bytes), "application/octet-stream").statusCode());
    }

    @Test void conflictingBytesOrMediaTypeUnderOneKeyAreRejected() throws Exception {
        byte[] a = "first".getBytes(), b = "second".getBytes();
        assertEquals(201, put(KEY, a, sha(a), "text/plain").statusCode());
        assertEquals(409, put(KEY, b, sha(b), "text/plain").statusCode());
        assertEquals(409, put(KEY, a, sha(a), "application/json").statusCode());
        assertArrayEquals(a, get(KEY, "GET").body());
    }

    @Test void invalidIntegrityOrSizeNeverPublishes() throws Exception {
        byte[] bytes = "payload".getBytes();
        assertEquals(400, put(KEY, bytes, sha("other".getBytes()), "text/plain").statusCode());   // hash mismatch
        assertEquals(400, put(KEY, bytes, null, "text/plain").statusCode());                       // hash missing
        assertEquals(400, put(KEY, bytes, sha(bytes), null).statusCode());                         // media type missing
        assertEquals(400, put("inputs/not-a-uuid/x", bytes, sha(bytes), "text/plain").statusCode()); // bad key
        assertEquals(400, put("inputs/" + UUID.randomUUID() + "/../x", bytes, sha(bytes), "text/plain").statusCode());
        assertEquals(404, get(KEY, "HEAD").statusCode());
        assertEquals(404, get(KEY, "GET").statusCode());
        assertTrue(files("object-*").isEmpty());
        assertTrue(files("stage-*").isEmpty(), "rejected uploads leave no staging files");
    }

    @Test void oversizeDeclaredLengthIsRejectedBeforeReading() throws Exception {
        try (var socket = new Socket("127.0.0.1", server.getAddress().getPort())) {
            var out = socket.getOutputStream();
            out.write(("PUT /v1/objects/" + KEY + " HTTP/1.1\r\nHost: x\r\nContent-Type: text/plain\r\nX-Content-SHA256: " + "a".repeat(64) +
                "\r\nContent-Length: " + (ManifestValidator.MAX_ARTIFACT + 1) + "\r\n\r\n").getBytes());
            out.flush();
            socket.shutdownOutput();
            socket.setSoTimeout(10_000);
            var status = new BufferedReader(new InputStreamReader(socket.getInputStream())).readLine();
            assertTrue(status.contains(" 413 "), status);
        }
        assertEquals(404, get(KEY, "HEAD").statusCode());
    }

    @Test void partialUploadIsInvisibleUntilCompleteAndDiscardedOnDisconnect() throws Exception {
        byte[] bytes = new byte[200_000]; new Random(7).nextBytes(bytes);
        try (var socket = new Socket("127.0.0.1", server.getAddress().getPort())) {
            var out = socket.getOutputStream();
            out.write(("PUT /v1/objects/" + KEY + " HTTP/1.1\r\nHost: x\r\nContent-Type: application/octet-stream\r\nX-Content-SHA256: " + sha(bytes) +
                "\r\nContent-Length: " + bytes.length + "\r\n\r\n").getBytes());
            out.write(bytes, 0, bytes.length / 2);
            out.flush();
            // The server has started staging; the object must not be visible.
            for (int i = 0; i < 20 && files("stage-*").isEmpty(); i++) Thread.sleep(25);
            assertFalse(files("stage-*").isEmpty(), "upload is being staged");
            assertEquals(404, get(KEY, "HEAD").statusCode());
            assertEquals(404, get(KEY, "GET").statusCode());
        } // client disconnects mid-upload
        for (int i = 0; i < 40 && !files("stage-*").isEmpty(); i++) Thread.sleep(25);
        assertEquals(404, get(KEY, "HEAD").statusCode());
        assertTrue(files("object-*").isEmpty());
        assertTrue(files("stage-*").isEmpty(), "abandoned staging file removed");
        // A later complete upload of the same key publishes normally.
        assertEquals(201, put(KEY, bytes, sha(bytes), "application/octet-stream").statusCode());
        assertArrayEquals(bytes, get(KEY, "GET").body());
    }

    @Test void concurrentPublicationIsImmutable() throws Exception {
        int writers = 12;
        try (var pool = Executors.newFixedThreadPool(writers)) {
            var start = new CountDownLatch(1);
            var futures = new ArrayList<Future<Integer>>();
            for (int i = 0; i < writers; i++) {
                byte[] body = ("writer-" + (i % 3)).getBytes();      // three distinct contents
                futures.add(pool.submit(() -> { start.await(); return put(KEY, body, sha(body), "text/plain").statusCode(); }));
            }
            start.countDown();
            var codes = new ArrayList<Integer>();
            for (var f : futures) codes.add(f.get(30, TimeUnit.SECONDS));
            assertEquals(1, Collections.frequency(codes, 201), codes.toString());
            byte[] winner = get(KEY, "GET").body();
            long sameAsWinner = codes.stream().filter(c -> c == 200).count();
            assertEquals(writers / 3 - 1, sameAsWinner, "identical replays of the winning bytes get 200");
            assertEquals(writers - writers / 3, Collections.frequency(codes, 409));
            assertTrue(new String(winner).startsWith("writer-"));
        }
        assertEquals(1, files("object-*").size());
    }

    @Test void publishedFilesRemainOnDiskAfterServiceStops() throws Exception {
        byte[] bytes = "durable for the run".getBytes();
        assertEquals(201, put(KEY, bytes, sha(bytes), "text/plain").statusCode());
        server.stop(0);
        var objects = files("object-*");
        assertEquals(1, objects.size());
        assertArrayEquals(bytes, Files.readAllBytes(objects.getFirst()));
        server = ArtifactMain.start(0, data);   // restarted service has an empty index (no restart-recovery claim)
        base = "http://127.0.0.1:" + server.getAddress().getPort() + "/v1/objects/";
        assertEquals(404, get(KEY, "HEAD").statusCode());
    }

    @Test void healthAndMethodErrors() throws Exception {
        var health = http.send(HttpRequest.newBuilder(URI.create(base.replace("/v1/objects/", "/v1/health"))).build(), HttpResponse.BodyHandlers.ofString());
        assertEquals(200, health.statusCode());
        assertEquals(405, get(KEY, "DELETE").statusCode());
        assertEquals(404, http.send(HttpRequest.newBuilder(URI.create(base.replace("/v1/objects/", "/v1/other"))).build(),
            HttpResponse.BodyHandlers.ofString()).statusCode());
    }
}
