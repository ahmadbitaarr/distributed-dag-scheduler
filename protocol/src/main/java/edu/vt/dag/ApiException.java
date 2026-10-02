package edu.vt.dag;

public final class ApiException extends RuntimeException {
    public final int status;
    public final String code;
    public ApiException(int status, String code, String message) {
        super(message); this.status = status; this.code = code;
    }
    public static ApiException bad(String message) { return new ApiException(400, "INVALID_INPUT", message); }
    public static ApiException conflict(String message) { return new ApiException(409, "CONFLICT", message); }
    public static void require(boolean value, String message) { if (!value) throw bad(message); }
}
