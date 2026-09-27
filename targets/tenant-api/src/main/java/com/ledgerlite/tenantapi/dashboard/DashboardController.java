package com.ledgerlite.tenantapi.dashboard;

import com.ledgerlite.tenantapi.invoice.InvoiceRepository;
import com.ledgerlite.tenantapi.tenant.TenantContext;
import java.math.BigDecimal;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * A-06 (seeded flaw, SPEC.md A-06): the totals cache key is a constant
 * string, not tenant-qualified. Whichever tenant's request populates the
 * cache first is what every other tenant sees until the fixed TTL expires,
 * regardless of who is actually asking. A correct cache key would be
 * {@code "summary:" + tenantId}.
 */
@RestController
@RequestMapping("/dashboard")
public class DashboardController {

    private static final String CACHE_KEY = "summary";
    private static final long TTL_MILLIS = 30_000L;

    private final InvoiceRepository invoiceRepository;
    private final TenantContext tenantContext;
    private final Map<String, CachedTotal> cache = new ConcurrentHashMap<>();

    public DashboardController(InvoiceRepository invoiceRepository, TenantContext tenantContext) {
        this.invoiceRepository = invoiceRepository;
        this.tenantContext = tenantContext;
    }

    @GetMapping("/summary")
    public Map<String, Object> summary() {
        String tenantId = tenantContext.currentTenantId();
        CachedTotal cached = cache.get(CACHE_KEY);
        long now = System.currentTimeMillis();
        if (cached != null && now - cached.computedAtMillis() < TTL_MILLIS) {
            return Map.of("totalAmount", cached.total(), "source", "cache");
        }
        BigDecimal total = invoiceRepository.sumAmountByTenantId(tenantId);
        cache.put(CACHE_KEY, new CachedTotal(total, now));
        return Map.of("totalAmount", total, "source", "computed");
    }

    private record CachedTotal(BigDecimal total, long computedAtMillis) {
    }
}
