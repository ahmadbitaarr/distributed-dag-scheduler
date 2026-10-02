package edu.vt.dag;

import java.util.*;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import static org.junit.jupiter.api.Assertions.*;
import static edu.vt.dag.Model.*;

/** Version 1 wire contract: manifests are parsed from JSON exactly as the scheduler receives them. */
class WireContractTest {
    static final String JOB = "6f1c2b9e-3d4a-4e5f-8a7b-0c1d2e3f4a5b";
    static final String ASSET = "0b7e5c2a-1d3f-4a6b-9c8d-7e6f5a4b3c2d";

    static String task(String id, String op, String params, String parents, String inputs, String output) {
        return "{\"task_id\":\"" + id + "\",\"operation\":\"" + op + "\",\"parameters\":" + params +
            ",\"parents\":" + parents + ",\"inputs\":" + inputs + ",\"outputs\":[\"" + output + "\"]}";
    }
    static String bind(String parent, String output) { return "{\"task_id\":\"" + parent + "\",\"output_name\":\"" + output + "\"}"; }
    static String manifest(String finalTask, String finalOutput, String... tasks) {
        return "{\"schema_version\":1,\"job_id\":\"" + JOB + "\",\"tasks\":[" + String.join(",", tasks) +
            "],\"final_outputs\":{\"result\":" + bind(finalTask, finalOutput) + "}}";
    }
    static Manifest parse(String json) { return Json.read(json.getBytes(), Manifest.class); }
    static ApiException rejected(String json) {
        return assertThrows(ApiException.class, () -> ManifestValidator.validate(parse(json)));
    }
    static void assertBad(String json) {
        var e = rejected(json);
        assertEquals(400, e.status, e.getMessage());
        assertEquals("INVALID_INPUT", e.code);
    }

    /** Functional workload from architecture §12: A=3, B=A+4, C=A*5, D=B+C, E formats. */
    static final String FUNCTIONAL = manifest("E", "text",
        task("A", "fixture_write", "{\"value\":3,\"delay_ms\":100}", "[]", "{}", "value"),
        task("B", "fixture_add", "{\"amount\":4}", "[\"A\"]", "{\"value\":" + bind("A", "value") + "}", "value"),
        task("C", "fixture_multiply", "{\"amount\":5}", "[\"A\"]", "{\"value\":" + bind("A", "value") + "}", "value"),
        task("D", "fixture_sum", "{}", "[\"B\",\"C\"]", "{\"left\":" + bind("B", "value") + ",\"right\":" + bind("C", "value") + "}", "value"),
        task("E", "fixture_format", "{}", "[\"D\"]", "{\"value\":" + bind("D", "value") + "}", "text"));

    // ---- valid graphs ----

    @Test void functionalChainAndJoinIsValid() { assertDoesNotThrow(() -> ManifestValidator.validate(parse(FUNCTIONAL))); }

    @Test void multipleRootsAndSinksAreValid() {
        assertDoesNotThrow(() -> ManifestValidator.validate(parse(manifest("C", "value",
            task("A", "fixture_write", "{\"value\":1}", "[]", "{}", "value"),
            task("B", "fixture_write", "{\"value\":2}", "[]", "{}", "value"),
            task("C", "fixture_add", "{\"amount\":1}", "[\"A\"]", "{\"value\":" + bind("A", "value") + "}", "value"),
            task("D", "fixture_add", "{\"amount\":1}", "[\"B\"]", "{\"value\":" + bind("B", "value") + "}", "value")))));
    }

    @Test void orderingOnlyDependencyIsValid() {
        assertDoesNotThrow(() -> ManifestValidator.validate(parse(manifest("B", "value",
            task("A", "fixture_write", "{\"value\":1}", "[]", "{}", "value"),
            task("B", "fixture_write", "{\"value\":2}", "[\"A\"]", "{}", "value")))));
    }

    @Test void videoDagWithSourceArtifactIsValid() {
        String src = "{\"source\":{\"key\":\"inputs/" + ASSET + "/sample.mp4\",\"length\":1000,\"sha256\":\"" + "a".repeat(64) + "\",\"media_type\":\"video/mp4\"}}";
        String srt = "{\"source\":{\"key\":\"inputs/" + ASSET + "/fixture.srt\",\"length\":10,\"sha256\":\"" + "b".repeat(64) + "\",\"media_type\":\"application/x-subrip\"}}";
        assertDoesNotThrow(() -> ManifestValidator.validate(parse(manifest("publish", "manifest",
            task("inspect", "video_inspect", "{}", "[]", "{\"video\":" + src + "}", "metadata"),
            task("t720", "video_transcode", "{\"height\":720}", "[\"inspect\"]", "{\"video\":" + src + "}", "video"),
            task("t360", "video_transcode", "{\"height\":360}", "[\"inspect\"]", "{\"video\":" + src + "}", "video"),
            task("thumb", "video_thumbnail", "{}", "[\"inspect\"]", "{\"video\":" + src + "}", "image"),
            task("subs", "fixture_subtitles", "{}", "[\"inspect\"]", "{\"srt\":" + srt + "}", "subtitles"),
            task("publish", "video_publish", "{}", "[\"t720\",\"t360\",\"thumb\",\"subs\"]",
                "{\"video720\":" + bind("t720", "video") + ",\"video360\":" + bind("t360", "video") +
                ",\"image\":" + bind("thumb", "image") + ",\"subtitles\":" + bind("subs", "subtitles") + "}", "manifest")))));
    }

    // ---- structural rejections ----

    @Test void rejectsEmptyAndMissingTaskLists() {
        assertBad("{\"schema_version\":1,\"job_id\":\"" + JOB + "\",\"tasks\":[],\"final_outputs\":{}}");
        assertBad("{\"schema_version\":1,\"job_id\":\"" + JOB + "\",\"final_outputs\":{}}");
    }

    @Test void rejectsDuplicateTaskIds() {
        assertBad(manifest("A", "value", task("A", "fixture_write", "{\"value\":1}", "[]", "{}", "value"),
            task("A", "fixture_write", "{\"value\":2}", "[]", "{}", "value")));
    }

    @Test void rejectsSelfEdgeUnknownParentAndCycle() {
        assertBad(manifest("A", "value", task("A", "fixture_write", "{\"value\":1}", "[\"A\"]", "{}", "value")));
        assertBad(manifest("A", "value", task("A", "fixture_write", "{\"value\":1}", "[\"Z\"]", "{}", "value")));
        assertBad(manifest("A", "value",
            task("A", "fixture_write", "{\"value\":1}", "[\"C\"]", "{}", "value"),
            task("B", "fixture_write", "{\"value\":1}", "[\"A\"]", "{}", "value"),
            task("C", "fixture_write", "{\"value\":1}", "[\"B\"]", "{}", "value")));
    }

    @ParameterizedTest
    @ValueSource(strings = {"a/b", "..", "a..b", "-lead", "", "x12345678901234567890123456789012345678901234567890123456789012345"})
    void rejectsInvalidTaskIds(String id) {
        assertBad(manifest(id, "value", task(id, "fixture_write", "{\"value\":1}", "[]", "{}", "value")));
    }

    @Test void rejectsWrongSchemaVersion() {
        assertBad(FUNCTIONAL.replace("\"schema_version\":1", "\"schema_version\":2"));
    }

    // ---- bindings ----

    @Test void rejectsIncompleteParentBindingsAsBadInputNotServerError() {
        // Previously a NullPointerException, which the HTTP layer reported as 503.
        for (String b : List.of("{\"task_id\":\"A\"}", "{\"output_name\":\"value\"}", "{}"))
            assertBad(manifest("B", "value", task("A", "fixture_write", "{\"value\":1}", "[]", "{}", "value"),
                task("B", "fixture_add", "{\"amount\":1}", "[\"A\"]", "{\"value\":" + b + "}", "value")));
    }

    @Test void rejectsMixedBindingAndSourceOutsideInputsNamespace() {
        String art = "{\"key\":\"inputs/" + ASSET + "/v.mp4\",\"length\":1,\"sha256\":\"" + "a".repeat(64) + "\",\"media_type\":\"video/mp4\"}";
        assertBad(manifest("B", "value", task("A", "fixture_write", "{\"value\":1}", "[]", "{}", "value"),
            task("B", "fixture_add", "{\"amount\":1}", "[\"A\"]", "{\"value\":{\"source\":" + art + ",\"task_id\":\"A\",\"output_name\":\"value\"}}", "value")));
        String runKey = "runs/" + ASSET + "/jobs/" + JOB + "/tasks/A/attempts/1/value";
        assertBad(manifest("I", "metadata", task("I", "video_inspect", "{}", "[]",
            "{\"video\":{\"source\":" + art.replace("inputs/" + ASSET + "/v.mp4", runKey) + "}}", "metadata")));
    }

    @Test void rejectsInvalidFinalBindings() {
        String a = task("A", "fixture_write", "{\"value\":1}", "[]", "{}", "value");
        String base = "{\"schema_version\":1,\"job_id\":\"" + JOB + "\",\"tasks\":[" + a + "],\"final_outputs\":";
        assertBad(base + "{}}");
        assertBad(base + "{\"result\":{\"task_id\":\"A\"}}}");
        assertBad(base + "{\"result\":{\"output_name\":\"value\"}}}");
        assertBad(base + "{\"result\":" + bind("Z", "value") + "}}");
        assertBad(base + "{\"result\":" + bind("A", "text") + "}}");
        assertBad(base + "{\"bad/name\":" + bind("A", "value") + "}}");
    }

    // ---- operation allowlist and parameters ----

    @Test void rejectsUnsupportedOperationsAndParameterMisuse() {
        assertBad(manifest("A", "value", task("A", "shell", "{}", "[]", "{}", "value")));
        assertBad(manifest("A", "value", task("A", "fixture_write", "{}", "[]", "{}", "value")));                    // value required
        assertBad(manifest("A", "value", task("A", "fixture_write", "{\"value\":1,\"amount\":2}", "[]", "{}", "value"))); // unexpected amount
        assertBad(manifest("A", "value", task("A", "fixture_write", "{\"value\":1,\"delay_ms\":30001}", "[]", "{}", "value")));
        assertBad(manifest("A", "value", task("A", "fixture_write", "{\"value\":1,\"delay_ms\":-1}", "[]", "{}", "value")));
        assertBad(manifest("A", "out", task("A", "fixture_write", "{\"value\":1}", "[]", "{}", "out")));             // wrong output name
        String src = "{\"source\":{\"key\":\"inputs/" + ASSET + "/v.mp4\",\"length\":1,\"sha256\":\"" + "a".repeat(64) + "\",\"media_type\":\"video/mp4\"}}";
        assertBad(manifest("T", "video", task("T", "video_transcode", "{\"height\":480}", "[]", "{\"video\":" + src + "}", "video")));
        assertBad(manifest("T", "video", task("T", "video_transcode", "{\"height\":720,\"delay_ms\":5}", "[]", "{\"video\":" + src + "}", "video")));
        assertBad(manifest("T", "image", task("T", "video_thumbnail", "{}", "[]", "{\"clip\":" + src + "}", "image"))); // wrong input name
    }

    // ---- malformed JSON and strict typing ----

    @Test void strictJsonRejectsCoercionUnknownFieldsDuplicatesAndTrailingTokens() {
        for (String bad : List.of(
                FUNCTIONAL.replace("\"value\":3", "\"value\":\"3\""),   // string is not a number
                FUNCTIONAL.replace("\"value\":3", "\"value\":3.0"),     // float is not an integer
                FUNCTIONAL.replace("\"amount\":4", "\"amount\":4,\"command\":\"rm\""), // unknown parameter
                FUNCTIONAL.replace("\"schema_version\":1", "\"schema_version\":1,\"schema_version\":1"),
                FUNCTIONAL.replace(JOB, "1-1-1-1-1"),
                FUNCTIONAL + "{}",
                "not json")) {
            var e = assertThrows(ApiException.class, () -> parse(bad), bad);
            assertEquals(400, e.status);
        }
    }

    // ---- replay equality ----

    @Test void semanticEqualityIgnoresTaskParentAndMapOrder() {
        String reordered = manifest("E", "text",
            task("E", "fixture_format", "{}", "[\"D\"]", "{\"value\":" + bind("D", "value") + "}", "text"),
            task("D", "fixture_sum", "{}", "[\"C\",\"B\"]", "{\"right\":" + bind("C", "value") + ",\"left\":" + bind("B", "value") + "}", "value"),
            task("C", "fixture_multiply", "{\"amount\":5}", "[\"A\"]", "{\"value\":" + bind("A", "value") + "}", "value"),
            task("B", "fixture_add", "{\"amount\":4}", "[\"A\"]", "{\"value\":" + bind("A", "value") + "}", "value"),
            task("A", "fixture_write", "{\"delay_ms\":100,\"value\":3}", "[]", "{}", "value"));
        assertEquals(parse(FUNCTIONAL), parse(reordered));
        assertEquals(parse(FUNCTIONAL), parse(" \n" + FUNCTIONAL.replace(",", " ,\n ")));
    }

    @Test void semanticEqualityDistinguishesMeaningfulChanges() {
        var original = parse(FUNCTIONAL);
        assertNotEquals(original, parse(FUNCTIONAL.replace("\"amount\":4", "\"amount\":40")));
        assertNotEquals(original, parse(FUNCTIONAL.replace("\"delay_ms\":100", "\"delay_ms\":101")));
        assertNotEquals(original, parse(FUNCTIONAL.replace("fixture_multiply", "fixture_add")));
        assertNotEquals(original, parse(FUNCTIONAL.replace("\"left\":", "\"first\":")));
    }

    @Test void manifestRoundTripsThroughJson() {
        var m = parse(FUNCTIONAL);
        assertEquals(m, Json.read(Json.bytes(m), Manifest.class));
    }

    // ---- artifact namespaces ----

    @Test void objectKeysUseCanonicalRestrictedNamespaces() {
        var id = new Identity(UUID.fromString(ASSET), UUID.fromString(JOB), "A", 2, UUID.randomUUID());
        assertTrue(ManifestValidator.validKey("inputs/" + ASSET + "/clip.mp4"));
        assertTrue(ManifestValidator.validKey(Model.prefix(id) + "value"));
        assertEquals("runs/" + ASSET + "/jobs/" + JOB + "/tasks/A/attempts/2/", Model.prefix(id));
        for (String bad : List.of(
                "inputs/1-1-1-1-1/clip.mp4",                            // lenient UUID form
                "inputs/" + ASSET.toUpperCase() + "/clip.mp4",
                "inputs/" + ASSET + "/../clip.mp4",
                "inputs/" + ASSET + "/a/b",
                "inputs/" + ASSET + "/",
                "outputs/" + ASSET + "/clip.mp4",
                "runs/" + ASSET + "/jobs/" + JOB + "/tasks/A/attempts/0/value",
                "runs/" + ASSET + "/jobs/" + JOB + "/tasks/A/attempts/01/value",
                "runs/" + ASSET + "/jobs/" + JOB + "/tasks/A/attempts/1/value/extra",
                "inputs/" + ASSET + "/" + "x".repeat(600)))
            assertFalse(ManifestValidator.validKey(bad), bad);
    }

    @Test void artifactDescriptorsAreValidated() {
        String key = "inputs/" + ASSET + "/v.mp4";
        assertDoesNotThrow(() -> ManifestValidator.artifact(new Artifact(key, 0, "a".repeat(64), "video/mp4")));
        assertBad400(() -> ManifestValidator.artifact(new Artifact(key, -1, "a".repeat(64), "video/mp4")));
        assertBad400(() -> ManifestValidator.artifact(new Artifact(key, 1, "A".repeat(64), "video/mp4")));
        assertBad400(() -> ManifestValidator.artifact(new Artifact(key, 1, "a".repeat(63), "video/mp4")));
        assertBad400(() -> ManifestValidator.artifact(new Artifact(key, 1, "a".repeat(64), "video")));
        assertEquals(413, assertThrows(ApiException.class, () -> ManifestValidator.artifact(
            new Artifact(key, ManifestValidator.MAX_ARTIFACT + 1, "a".repeat(64), "video/mp4"))).status);
    }

    // ---- ownership tuple and claims ----

    @Test void identityRequiresEveryOwnershipField() {
        UUID run = UUID.randomUUID(), job = UUID.randomUUID(), session = UUID.randomUUID();
        assertDoesNotThrow(() -> ManifestValidator.identity(new Identity(run, job, "A", 1, session)));
        for (var id : Arrays.asList(null,
                new Identity(null, job, "A", 1, session),
                new Identity(run, null, "A", 1, session),
                new Identity(run, job, null, 1, session),
                new Identity(run, job, "a/b", 1, session),
                new Identity(run, job, "A", 0, session),
                new Identity(run, job, "A", -1, session),
                new Identity(run, job, "A", 1, null)))
            assertBad400(() -> ManifestValidator.identity(id));
    }

    @Test void identityMissingAttemptFromJsonIsRejected() {
        // A missing primitive deserializes as 0, which identity validation rejects.
        String json = "{\"scheduler_run_id\":\"" + ASSET + "\",\"job_id\":\"" + JOB + "\",\"task_id\":\"A\",\"worker_session_id\":\"" + ASSET + "\"}";
        assertBad400(() -> ManifestValidator.identity(Json.read(json.getBytes(), Identity.class)));
    }

    @Test void claimRequiresAllUuids() {
        UUID a = UUID.randomUUID();
        assertDoesNotThrow(() -> ManifestValidator.claim(new Claim(a, a, a)));
        for (var c : Arrays.asList(null, new Claim(null, a, a), new Claim(a, null, a), new Claim(a, a, null)))
            assertBad400(() -> ManifestValidator.claim(c));
    }

    static void assertBad400(org.junit.jupiter.api.function.Executable call) {
        assertEquals(400, assertThrows(ApiException.class, call).status);
    }
}
