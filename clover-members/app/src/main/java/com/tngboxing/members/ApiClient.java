package com.tngboxing.members;

import org.json.JSONObject;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import javax.net.ssl.HttpsURLConnection;

final class ApiClient {
    static final class Failure extends Exception {
        final int status;
        Failure(int status, String message) { super(message); this.status = status; }
    }
    static JSONObject call(String token, String method, String path, JSONObject body) throws Exception {
        HttpsURLConnection connection = (HttpsURLConnection)new URL(BuildConfig.API_BASE_URL + "/api/clover-pos" + path).openConnection();
        try {
            connection.setConnectTimeout(10000); connection.setReadTimeout(15000);
            connection.setRequestMethod(method); connection.setInstanceFollowRedirects(false);
            connection.setRequestProperty("Accept", "application/json");
            if (!token.isEmpty()) connection.setRequestProperty("Authorization", "Bearer " + token);
            if (body != null) {
                connection.setDoOutput(true); connection.setRequestProperty("Content-Type", "application/json");
                try (java.io.OutputStream stream = connection.getOutputStream()) { stream.write(body.toString().getBytes(StandardCharsets.UTF_8)); }
            }
            int status = connection.getResponseCode();
            InputStream input = status >= 400 ? connection.getErrorStream() : connection.getInputStream();
            ByteArrayOutputStream output = new ByteArrayOutputStream();
            if (input != null) try (InputStream stream = input) {
                byte[] buffer = new byte[4096]; int count;
                while ((count = stream.read(buffer)) != -1) {
                    if (output.size() + count > 2000000) throw new Failure(status, "The response was too large. Narrow your search.");
                    output.write(buffer, 0, count);
                }
            }
            JSONObject data;
            try { data = new JSONObject(output.toString("UTF-8")); }
            catch (Exception ignored) { throw new Failure(status, "The gym service returned an unexpected response. Try again."); }
            if (status < 200 || status >= 300) {
                Object detail = data.opt("detail");
                throw new Failure(status, detail instanceof String ? (String)detail : "Request could not be completed (" + status + ").");
            }
            return data;
        } finally { connection.disconnect(); }
    }
}
