package com.ledgerlite.tenantapi.webhook;

import jakarta.validation.Valid;
import java.net.URI;
import java.net.http.HttpClient;
import java.util.List;
import java.util.Map;
import java.util.regex.Pattern;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.client.RestClient;

/**
 * A-13 fix: every request is rejected with HTTP 400 BEFORE any outbound
 * call is made, unless it is https, has a host on the static allow-list
 * (app.webhooks.allowed-hosts), and is not a bare IP literal (which would
 * bypass a hostname-based allow-list entirely, e.g. https://169.254.169.254/).
 * Redirects are disabled so an allowed host can't 302 an attacker
 * elsewhere. A per-tenant "registered webhooks" table would be more
 * realistic but is not needed to close this finding for a demo app with
 * no webhook-registration feature at all.
 */
@RestController
@RequestMapping("/webhooks")
public class WebhookController {

    private static final Pattern IP_LITERAL = Pattern.compile("^[0-9.:\\[\\]a-fA-F]+$");

    private final RestClient restClient;
    private final List<String> allowedHosts;

    public WebhookController(@Value("#{'${app.webhooks.allowed-hosts:}'.split(',')}") List<String> allowedHosts) {
        // Deliberately does NOT reuse the shared RestClient.Builder bean
        // (see RestClientConfig) - that bean is a mutable singleton, and
        // calling .requestFactory() on a shared instance would leak the
        // no-redirects setting into every other consumer of it (or get
        // silently overwritten by one), depending on bean init order.
        this.restClient = RestClient.builder()
                .requestFactory(new org.springframework.http.client.JdkClientHttpRequestFactory(
                        HttpClient.newBuilder().followRedirects(HttpClient.Redirect.NEVER).build()))
                .build();
        this.allowedHosts = allowedHosts.stream().map(String::trim).filter(s -> !s.isBlank()).toList();
    }

    @PreAuthorize("hasAnyRole('owner','admin')")
    @PostMapping("/test")
    public ResponseEntity<Map<String, Object>> test(@Valid @RequestBody WebhookTestRequest request) {
        URI uri;
        try {
            uri = URI.create(request.url());
        } catch (IllegalArgumentException e) {
            return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(Map.of("error", "invalid_url"));
        }
        String host = uri.getHost();
        if (!"https".equalsIgnoreCase(uri.getScheme())
                || host == null
                || IP_LITERAL.matcher(host).matches()
                || !allowedHosts.contains(host)) {
            return ResponseEntity.status(HttpStatus.BAD_REQUEST)
                    .body(Map.of("error", "host_not_allowed", "host", String.valueOf(host)));
        }
        try {
            String body = restClient.get().uri(uri).retrieve().body(String.class);
            String snippet = body == null ? "" : body.substring(0, Math.min(500, body.length()));
            return ResponseEntity.ok(Map.of("url", request.url(), "ok", true, "bodySnippet", snippet));
        } catch (Exception e) {
            return ResponseEntity.ok(Map.of("url", request.url(), "ok", false, "error", String.valueOf(e.getMessage())));
        }
    }
}
