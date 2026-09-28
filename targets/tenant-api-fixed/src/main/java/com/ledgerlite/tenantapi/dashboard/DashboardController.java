package com.ledgerlite.tenantapi.dashboard;

import com.ledgerlite.tenantapi.invoice.InvoiceRepository;
import com.ledgerlite.tenantapi.tenant.TenantContext;
import com.ledgerlite.tenantapi.tenant.TenantScope;
import java.math.BigDecimal;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * A-06 fix: the cache key is tenant-qualified ({@code "summary:" + tenantId}),
 * so one tenant's request can never populate the value another tenant sees.
 */
@RestController
@RequestMapping("/dashboard")
public class DashboardController {

    private static final long TTL_MILLIS = 30_000L;

    private final InvoiceRepository invoiceRepository;
    private final TenantContext tenantContext;
    private final TenantScope tenantScope;
    private final Map<String, CachedTotal> cache = new ConcurrentHashMap<>();

    public DashboardController(InvoiceRepository invoiceRepository, TenantContext tenantContext, TenantScope tenantScope) {
        this.invoiceRepository = invoiceRepository;
        this.tenantContext = tenantContext;
        this.tenantScope = tenantScope;
    }

    @PreAuthorize("hasAnyRole('owner','admin','accountant','viewer')")
    @GetMapping("/summary")
    public Map<String, Object> summary() {
        String tenantId = tenantContext.currentTenantId();
        String cacheKey = "summary:" + tenantId;
        CachedTotal cached = cache.get(cacheKey);
        long now = System.currentTimeMillis();
        if (cached != null && now - cached.computedAtMillis() < TTL_MILLIS) {
            return Map.of("totalAmount", cached.total(), "source", "cache");
        }
        BigDecimal total = tenantScope.call(tenantId, () -> invoiceRepository.sumAmountByTenantId(tenantId));
        cache.put(cacheKey, new CachedTotal(total, now));
        return Map.of("totalAmount", total, "source", "computed");
    }

    private record CachedTotal(BigDecimal total, long computedAtMillis) {
    }
}
