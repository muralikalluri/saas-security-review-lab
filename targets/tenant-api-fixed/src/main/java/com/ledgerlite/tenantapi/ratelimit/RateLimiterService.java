package com.ledgerlite.tenantapi.ratelimit;

import io.github.bucket4j.Bandwidth;
import io.github.bucket4j.Bucket;
import java.time.Duration;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.stereotype.Service;

/**
 * A-10 fix: in-memory Bucket4j buckets, one per (limiter name + key) so
 * that e.g. one username's login attempts can't starve another's, and
 * one tenant's export bursts can't starve another's. Generous enough
 * (see the two call sites) that a normal demo/test run - including the
 * isolation-tester's own login-per-actor traffic - never gets throttled;
 * only the exploit scripts' deliberate bursts should trip it.
 */
@Service
public class RateLimiterService {

    private final Map<String, Bucket> buckets = new ConcurrentHashMap<>();

    public boolean tryConsume(String limiterName, String key, int capacity, Duration refillPeriod) {
        Bucket bucket = buckets.computeIfAbsent(
                limiterName + ":" + key,
                k -> Bucket.builder()
                        .addLimit(Bandwidth.classic(capacity, io.github.bucket4j.Refill.greedy(capacity, refillPeriod)))
                        .build());
        return bucket.tryConsume(1);
    }
}
