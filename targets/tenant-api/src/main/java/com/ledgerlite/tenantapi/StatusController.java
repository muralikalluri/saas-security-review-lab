package com.ledgerlite.tenantapi;

import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class StatusController {

    @GetMapping("/api/status")
    public Map<String, String> status() {
        return Map.of(
                "service", "tenant-api",
                "milestone", "M1-baseline",
                "note", "Deliberately insecure baseline - all seeded flaws A-01..A-13 present. See exploits/.");
    }
}
