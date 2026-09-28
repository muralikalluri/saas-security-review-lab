package com.ledgerlite.tenantapi.auth;

import com.ledgerlite.tenantapi.ratelimit.RateLimiterService;
import jakarta.validation.Valid;
import java.time.Duration;
import java.util.Map;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.RestClient;

/**
 * A-10 fix: rate limited per username (generous enough that a normal
 * demo/test run - including the isolation-tester logging in every actor
 * once at session start - never gets throttled; only a deliberate burst,
 * like the exploit script, should trip it).
 */
@RestController
@RequestMapping("/auth")
public class AuthController {

    private static final int LOGIN_CAPACITY = 15;
    private static final Duration LOGIN_REFILL = Duration.ofMinutes(1);

    private final RestClient restClient;
    private final String tokenUri;
    private final String clientId;
    private final RateLimiterService rateLimiter;

    public AuthController(
            RestClient.Builder restClientBuilder,
            @Value("${app.keycloak.internal-token-uri}") String tokenUri,
            @Value("${app.keycloak.client-id}") String clientId,
            RateLimiterService rateLimiter) {
        this.restClient = restClientBuilder.build();
        this.tokenUri = tokenUri;
        this.clientId = clientId;
        this.rateLimiter = rateLimiter;
    }

    @PostMapping("/login")
    public ResponseEntity<?> login(@Valid @RequestBody LoginRequest request) {
        if (!rateLimiter.tryConsume("auth-login", request.username(), LOGIN_CAPACITY, LOGIN_REFILL)) {
            return ResponseEntity.status(HttpStatus.TOO_MANY_REQUESTS).body(Map.of("error", "rate_limited"));
        }
        MultiValueMap<String, String> form = new LinkedMultiValueMap<>();
        form.add("grant_type", "password");
        form.add("client_id", clientId);
        form.add("username", request.username());
        form.add("password", request.password());
        try {
            String tokenResponse = restClient
                    .post()
                    .uri(tokenUri)
                    .contentType(MediaType.APPLICATION_FORM_URLENCODED)
                    .body(form)
                    .retrieve()
                    .body(String.class);
            return ResponseEntity.ok().contentType(MediaType.APPLICATION_JSON).body(tokenResponse);
        } catch (HttpClientErrorException e) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(Map.of("error", "invalid_credentials"));
        }
    }
}
