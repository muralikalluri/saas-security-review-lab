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
 * A-05 fix: {@link #read(Long, String)} now takes the caller's tenant and
 * compares it against {@link ExportRecord#tenantId()} - a foreign id
 * returns nothing, regardless of how easy the id is to guess. Files are
 * also written to a per-tenant subdirectory (defence in depth, not the
 * actual control - the ownership check above is).
 */
@Service
public class ExportService {

    private final InvoiceRepository invoiceRepository;
    private final AtomicLong sequence = new AtomicLong(0);
    private final Map<Long, ExportRecord> exports = new ConcurrentHashMap<>();
    private final Path exportDir;

    public ExportService(InvoiceRepository invoiceRepository) {
        this.invoiceRepository = invoiceRepository;
        this.exportDir = Path.of(System.getProperty("java.io.tmpdir"), "ledgerlite-fixed-exports");
        try {
            Files.createDirectories(exportDir);
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    public ExportRecord createExport(String tenantId) {
        long id = sequence.incrementAndGet();
        List<Invoice> invoices = invoiceRepository.findByTenantId(tenantId);
        Path tenantDir = exportDir.resolve(tenantId);
        Path file = tenantDir.resolve(id + ".csv");
        StringBuilder csv = new StringBuilder("id,customer_id,amount,status\n");
        for (Invoice invoice : invoices) {
            csv.append(invoice.getId())
                    .append(',')
                    .append(invoice.getCustomerId())
                    .append(',')
                    .append(invoice.getAmount())
                    .append(',')
                    .append(invoice.getStatus())
                    .append('\n');
        }
        try {
            Files.createDirectories(tenantDir);
            Files.writeString(file, csv.toString());
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
        ExportRecord record = new ExportRecord(id, tenantId, file);
        exports.put(id, record);
        return record;
    }

    /** A-05 fix: returns null (never someone else's record) unless the id belongs to callerTenantId. */
    public ExportRecord read(Long id, String callerTenantId) {
        ExportRecord record = exports.get(id);
        if (record == null || !record.tenantId().equals(callerTenantId)) {
            return null;
        }
        return record;
    }

    public record ExportRecord(Long id, String tenantId, Path file) {
    }
}
