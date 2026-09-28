package com.ledgerlite.tenantapi.export;

import com.ledgerlite.tenantapi.audit.AuditLog;
import com.ledgerlite.tenantapi.audit.AuditLogRepository;
import com.ledgerlite.tenantapi.ratelimit.RateLimiterService;
import com.ledgerlite.tenantapi.tenant.TenantContext;
import com.ledgerlite.tenantapi.tenant.TenantScope;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.time.Duration;
import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * A-05 fix (ownership check, see ExportService) and A-10 fix (rate
 * limiting on export creation) and A-11 fix (export creation is audited).
 */
@RestController
@RequestMapping("/invoices")
public class ExportController {

    private static final int EXPORT_CAPACITY = 10;
    private static final Duration EXPORT_REFILL = Duration.ofMinutes(1);

    private final ExportService exportService;
    private final TenantContext tenantContext;
    private final TenantScope tenantScope;
    private final RateLimiterService rateLimiter;
    private final AuditLogRepository auditLogRepository;

    public ExportController(
            ExportService exportService,
            TenantContext tenantContext,
            TenantScope tenantScope,
            RateLimiterService rateLimiter,
            AuditLogRepository auditLogRepository) {
        this.exportService = exportService;
        this.tenantContext = tenantContext;
        this.tenantScope = tenantScope;
        this.rateLimiter = rateLimiter;
        this.auditLogRepository = auditLogRepository;
    }

    @PreAuthorize("hasAnyRole('owner','admin','accountant')")
    @PostMapping("/export")
    public ResponseEntity<Map<String, Long>> createExport() {
        String tenantId = tenantContext.tokenTenantId();
        if (!rateLimiter.tryConsume("invoices-export", tenantId, EXPORT_CAPACITY, EXPORT_REFILL)) {
            return ResponseEntity.status(HttpStatus.TOO_MANY_REQUESTS).build();
        }
        ExportService.ExportRecord record = tenantScope.call(tenantId, () -> {
            ExportService.ExportRecord created = exportService.createExport(tenantId);
            auditLogRepository.save(new AuditLog(tenantId, tenantContext.currentUsername(), "export.create", "export:" + created.id()));
            return created;
        });
        return ResponseEntity.ok(Map.of("exportId", record.id()));
    }

    /** A-05 fix: read(id, callerTenantId) - a foreign id is a 404, sequential or not. */
    @PreAuthorize("hasAnyRole('owner','admin','accountant')")
    @GetMapping("/exports/{id}")
    public ResponseEntity<String> download(@PathVariable Long id) {
        String tenantId = tenantContext.tokenTenantId();
        ExportService.ExportRecord record = exportService.read(id, tenantId);
        if (record == null) {
            return ResponseEntity.notFound().build();
        }
        try {
            String csv = Files.readString(record.file());
            return ResponseEntity.ok().contentType(MediaType.valueOf("text/csv")).body(csv);
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }
}
