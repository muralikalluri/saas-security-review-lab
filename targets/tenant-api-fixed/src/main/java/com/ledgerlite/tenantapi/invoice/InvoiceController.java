package com.ledgerlite.tenantapi.invoice;

import com.ledgerlite.tenantapi.config.CrossTenantReferenceException;
import com.ledgerlite.tenantapi.customer.CustomerRepository;
import com.ledgerlite.tenantapi.tenant.TenantContext;
import com.ledgerlite.tenantapi.tenant.TenantScope;
import jakarta.validation.Valid;
import java.util.List;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
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
    private final CustomerRepository customerRepository;
    private final TenantContext tenantContext;
    private final TenantScope tenantScope;

    public InvoiceController(
            InvoiceRepository invoiceRepository,
            InvoiceSearchRepository invoiceSearchRepository,
            CustomerRepository customerRepository,
            TenantContext tenantContext,
            TenantScope tenantScope) {
        this.invoiceRepository = invoiceRepository;
        this.invoiceSearchRepository = invoiceSearchRepository;
        this.customerRepository = customerRepository;
        this.tenantContext = tenantContext;
        this.tenantScope = tenantScope;
    }

    /** A-04 fix: tenant comes only from the JWT (TenantContext no longer accepts any header). */
    @PreAuthorize("hasAnyRole('owner','admin','accountant','viewer')")
    @GetMapping
    public List<InvoiceResponse> list() {
        String tenantId = tenantContext.currentTenantId();
        return tenantScope.call(
                tenantId,
                () -> invoiceRepository.findByTenantId(tenantId).stream().map(InvoiceResponse::from).toList());
    }

    /** A-01 fix: explicit WHERE tenant_id via findByIdAndTenantId - a foreign id is a 404, not a 200. */
    @PreAuthorize("hasAnyRole('owner','admin','accountant','viewer')")
    @GetMapping("/{id}")
    public ResponseEntity<InvoiceResponse> get(@PathVariable Long id) {
        String tenantId = tenantContext.tokenTenantId();
        return tenantScope.call(
                tenantId,
                () -> invoiceRepository
                        .findByIdAndTenantId(id, tenantId)
                        .map(invoice -> ResponseEntity.ok(InvoiceResponse.from(invoice)))
                        .orElseGet(() -> ResponseEntity.notFound().build()));
    }

    /**
     * A-03 fix: tenantId is not accepted from the client at all (see
     * InvoiceCreateRequest) - it always comes from the caller's own JWT.
     * A customerId belonging to another tenant is rejected (400), not
     * silently accepted (SPEC doesn't call this out explicitly, but a
     * cross-tenant FK is the same class of bug as A-03 and RLS alone
     * would only catch it at read time, not at write time).
     */
    @PreAuthorize("hasAnyRole('owner','admin','accountant')")
    @PostMapping
    public ResponseEntity<InvoiceResponse> create(@Valid @RequestBody InvoiceCreateRequest request) {
        String tenantId = tenantContext.tokenTenantId();
        return tenantScope.call(tenantId, () -> {
            boolean customerOwnedByTenant = customerRepository
                    .findByIdAndTenantId(request.customerId(), tenantId)
                    .isPresent();
            if (!customerOwnedByTenant) {
                throw new CrossTenantReferenceException("customerId does not belong to the caller's tenant");
            }
            Invoice invoice =
                    new Invoice(tenantId, request.customerId(), request.amount(), request.internalCost(), request.status());
            Invoice saved = invoiceRepository.save(invoice);
            return ResponseEntity.ok(InvoiceResponse.from(saved));
        });
    }

    /** A-12 fix: sort is whitelisted (see InvoiceSearchRepository); the tenant filter was already parameterised. */
    @PreAuthorize("hasAnyRole('owner','admin','accountant','viewer')")
    @GetMapping("/search")
    public List<InvoiceSearchRepository.InvoiceRow> search(@RequestParam(defaultValue = "id") String sort) {
        String tenantId = tenantContext.tokenTenantId();
        return tenantScope.call(tenantId, () -> invoiceSearchRepository.searchByTenant(tenantId, sort));
    }
}
