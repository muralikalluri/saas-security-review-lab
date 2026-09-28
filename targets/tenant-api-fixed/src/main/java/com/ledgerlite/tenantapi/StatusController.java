package com.ledgerlite.tenantapi;

import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class StatusController {

    @GetMapping("/api/status")
    public Map<String, String> status() {
        return Map.of(
                "service", "tenant-api-fixed",
                "milestone", "M3-fixed",
                "note", "Fixed mode - every seeded flaw A-01..A-13 closed. See ../tenant-api/exploits/.");
    }
}
