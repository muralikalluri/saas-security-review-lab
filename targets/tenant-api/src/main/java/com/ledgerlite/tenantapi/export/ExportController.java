package com.ledgerlite.tenantapi.export;

import com.ledgerlite.tenantapi.tenant.TenantContext;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.util.Map;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * A-05 / A-10 (seeded flaws, SPEC.md A-05, A-10): no ownership check on
 * download (A-05, see {@link ExportService}) and no rate limiting on
 * export creation (A-10) - a caller can create/download as many exports
 * per second as they like.
 */
@RestController
@RequestMapping("/invoices")
public class ExportController {

    private final ExportService exportService;
    private final TenantContext tenantContext;

    public ExportController(ExportService exportService, TenantContext tenantContext) {
        this.exportService = exportService;
        this.tenantContext = tenantContext;
    }

    @PostMapping("/export")
    public Map<String, Long> createExport() {
        String tenantId = tenantContext.tokenTenantId();
        ExportService.ExportRecord record = exportService.createExport(tenantId);
        return Map.of("exportId", record.id());
    }

    /**
     * A-05 (seeded flaw, SPEC.md A-05): deliberately does NOT compare
     * {@code record.tenantId()} against the caller's own tenant before
     * streaming the file back. Sequential ids mean any tenant's export can
     * be read by walking id-1, id-2, ... regardless of who is asking.
     */
    @GetMapping("/exports/{id}")
    public ResponseEntity<String> download(@PathVariable Long id) {
        ExportService.ExportRecord record = exportService.read(id);
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
