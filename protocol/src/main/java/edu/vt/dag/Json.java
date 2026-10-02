package edu.vt.dag;

import com.fasterxml.jackson.core.JsonParser;
import com.fasterxml.jackson.databind.*;
import com.fasterxml.jackson.databind.json.JsonMapper;

public final class Json {
    public static final ObjectMapper MAPPER = JsonMapper.builder()
        .enable(DeserializationFeature.FAIL_ON_TRAILING_TOKENS)
        .enable(JsonParser.Feature.STRICT_DUPLICATE_DETECTION)
        .disable(DeserializationFeature.ACCEPT_FLOAT_AS_INT)
        .disable(MapperFeature.ALLOW_COERCION_OF_SCALARS).build();
    private Json() {}
    public static byte[] bytes(Object value) {
        try { return MAPPER.writeValueAsBytes(value); }
        catch (Exception e) { throw new IllegalStateException("Cannot encode JSON", e); }
    }
    public static String string(Object value) { return new String(bytes(value), java.nio.charset.StandardCharsets.UTF_8); }
    public static <T> T read(byte[] bytes, Class<T> type) {
        try { return MAPPER.readValue(bytes, type); }
        catch (Exception e) { throw ApiException.bad("Malformed JSON or unsupported field/type: " + e.getMessage()); }
    }
}
