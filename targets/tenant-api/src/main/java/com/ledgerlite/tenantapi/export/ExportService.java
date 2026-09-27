package com.ledgerlite.tenantapi.export;

import com.ledgerlite.tenantapi.invoice.Invoice;
import com.ledgerlite.tenantapi.invoice.InvoiceRepository;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;
import org.springframework.stereotype.Service;

/**
 * A-05 (seeded flaw, SPEC.md A-05): export files are named by a single
 * process-wide sequential counter (not per-tenant, not random/UUID) and
 * written to one shared temp directory. {@link #read(Long)} intentionally
 * has no idea who is asking - the caller's tenant is never compared against
 * {@link ExportRecord#tenantId()}, so anyone who can guess/increment the id
 * can download another tenant's export. See {@link ExportController} for
 * where that missing check would go.
 */
@Service
public class ExportService {

    private final InvoiceRepository invoiceRepository;
    private final AtomicLong sequence = new AtomicLong(0);
    private final Map<Long, ExportRecord> exports = new ConcurrentHashMap<>();
    private final Path exportDir;

    public ExportService(InvoiceRepository invoiceRepository) {
        this.invoiceRepository = invoiceRepository;
        this.exportDir = Path.of(System.getProperty("java.io.tmpdir"), "ledgerlite-exports");
        try {
            Files.createDirectories(exportDir);
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    public ExportRecord createExport(String tenantId) {
        long id = sequence.incrementAndGet();
        List<Invoice> invoices = invoiceRepository.findByTenantId(tenantId);
        Path file = exportDir.resolve(id + ".csv");
        StringBuilder csv = new StringBuilder("id,customer_id,amount,internal_cost,status\n");
        for (Invoice invoice : invoices) {
            csv.append(invoice.getId())
                    .append(',')
                    .append(invoice.getCustomerId())
                    .append(',')
                    .append(invoice.getAmount())
                    .append(',')
                    .append(invoice.getInternalCost())
                    .append(',')
                    .append(invoice.getStatus())
                    .append('\n');
        }
        try {
            Files.writeString(file, csv.toString());
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
        ExportRecord record = new ExportRecord(id, tenantId, file);
        exports.put(id, record);
        return record;
    }

    public ExportRecord read(Long id) {
        return exports.get(id);
    }

    public record ExportRecord(Long id, String tenantId, Path file) {
    }
}
