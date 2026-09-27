package com.ledgerlite.tenantapi.invoice;

import com.ledgerlite.tenantapi.tenant.TenantContext;
import jakarta.validation.Valid;
import java.util.List;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/invoices")
public class InvoiceController {

    private final InvoiceRepository invoiceRepository;
    private final InvoiceSearchRepository invoiceSearchRepository;
    private final TenantContext tenantContext;

    public InvoiceController(
            InvoiceRepository invoiceRepository,
            InvoiceSearchRepository invoiceSearchRepository,
            TenantContext tenantContext) {
        this.invoiceRepository = invoiceRepository;
        this.invoiceSearchRepository = invoiceSearchRepository;
        this.tenantContext = tenantContext;
    }

    /**
     * A-04 (seeded flaw, SPEC.md A-04): scoped via {@link TenantContext#currentTenantId()},
     * spoofable with an X-Tenant-Id header.
     */
    @GetMapping
    public List<InvoiceResponse> list() {
        String tenantId = tenantContext.currentTenantId();
        return invoiceRepository.findByTenantId(tenantId).stream()
                .map(InvoiceResponse::from)
                .toList();
    }

    /**
     * A-01 (seeded flaw, SPEC.md A-01 / BOLA): loads purely by primary key.
     * No tenant_id check at all - any authenticated caller of any tenant
     * can read any invoice, including internalCost, by guessing/enumerating
     * ids.
     */
    @GetMapping("/{id}")
    public ResponseEntity<InvoiceResponse> get(@PathVariable Long id) {
        return invoiceRepository
                .findById(id)
                .map(invoice -> ResponseEntity.ok(InvoiceResponse.from(invoice)))
                .orElseGet(() -> ResponseEntity.notFound().build());
    }

    /**
     * A-03 (seeded flaw, SPEC.md A-03): trusts the client-supplied
     * {@code tenantId} on the request body instead of deriving it from the
     * caller's JWT (mass assignment); the response also echoes tenantId and
     * internalCost (BOPLA).
     */
    @PostMapping
    public ResponseEntity<InvoiceResponse> create(@Valid @RequestBody InvoiceCreateRequest request) {
        String tenantId = request.tenantId() != null ? request.tenantId() : tenantContext.tokenTenantId();
        Invoice invoice = new Invoice(
                tenantId, request.customerId(), request.amount(), request.internalCost(), request.status());
        Invoice saved = invoiceRepository.save(invoice);
        return ResponseEntity.ok(InvoiceResponse.from(saved));
    }

    /**
     * A-12 (seeded flaw, SPEC.md A-12): {@code sort} is concatenated
     * directly into the ORDER BY clause of a native query. The WHERE
     * tenant_id=? filter IS parameterised, so this is an injection finding
     * only, not a tenant-isolation leak.
     */
    @GetMapping("/search")
    public List<InvoiceSearchRepository.InvoiceRow> search(@RequestParam(defaultValue = "id") String sort) {
        String tenantId = tenantContext.tokenTenantId();
        return invoiceSearchRepository.searchByTenant(tenantId, sort);
    }
}
