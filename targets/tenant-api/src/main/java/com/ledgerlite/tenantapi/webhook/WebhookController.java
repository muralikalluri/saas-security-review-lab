package com.ledgerlite.tenantapi.webhook;

import jakarta.validation.Valid;
import java.util.Map;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.client.RestClient;

/**
 * A-13 (seeded flaw, SPEC.md A-13 / SSRF): "test this webhook URL" fetches
 * whatever URL the client supplies with no allow-list, no deny-list for
 * private/link-local ranges (e.g. 169.254.169.254 cloud metadata), and no
 * restriction on scheme or port. The fixed version (M3) replaces this with
 * an allow-list of the tenant's own registered webhook hosts.
 */
@RestController
@RequestMapping("/webhooks")
public class WebhookController {

    private final RestClient restClient;

    public WebhookController(RestClient.Builder restClientBuilder) {
        this.restClient = restClientBuilder.build();
    }

    @PostMapping("/test")
    public Map<String, Object> test(@Valid @RequestBody WebhookTestRequest request) {
        try {
            String body = restClient
                    .get()
                    .uri(request.url())
                    .retrieve()
                    .body(String.class);
            String snippet = body == null ? "" : body.substring(0, Math.min(500, body.length()));
            return Map.of("url", request.url(), "ok", true, "bodySnippet", snippet);
        } catch (Exception e) {
            return Map.of("url", request.url(), "ok", false, "error", e.getMessage());
        }
    }
}
