package com.ledgerlite.tenantapi.customer;

import com.ledgerlite.tenantapi.tenant.TenantContext;
import com.ledgerlite.tenantapi.tenant.TenantScope;
import jakarta.validation.Valid;
import java.util.List;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/customers")
public class CustomerController {

    private final CustomerRepository customerRepository;
    private final TenantContext tenantContext;
    private final TenantScope tenantScope;

    public CustomerController(CustomerRepository customerRepository, TenantContext tenantContext, TenantScope tenantScope) {
        this.customerRepository = customerRepository;
        this.tenantContext = tenantContext;
        this.tenantScope = tenantScope;
    }

    /** A-04 fix: tenant comes only from the JWT. */
    @PreAuthorize("hasAnyRole('owner','admin','accountant','viewer')")
    @GetMapping
    public List<CustomerResponse> list() {
        String tenantId = tenantContext.currentTenantId();
        return tenantScope.call(
                tenantId,
                () -> customerRepository.findByTenantId(tenantId).stream().map(CustomerResponse::from).toList());
    }

    @PreAuthorize("hasAnyRole('owner','admin','accountant','viewer')")
    @GetMapping("/{id}")
    public ResponseEntity<CustomerResponse> get(@PathVariable Long id) {
        String tenantId = tenantContext.tokenTenantId();
        return tenantScope.call(
                tenantId,
                () -> customerRepository
                        .findByIdAndTenantId(id, tenantId)
                        .map(c -> ResponseEntity.ok(CustomerResponse.from(c)))
                        .orElseGet(() -> ResponseEntity.notFound().build()));
    }

    /** A-02 fix: explicit WHERE tenant_id via findByIdAndTenantId - a foreign id is a 404, and nothing is written. */
    @PreAuthorize("hasAnyRole('owner','admin','accountant')")
    @PutMapping("/{id}")
    public ResponseEntity<CustomerResponse> update(
            @PathVariable Long id, @Valid @RequestBody CustomerUpdateRequest request) {
        String tenantId = tenantContext.tokenTenantId();
        return tenantScope.call(
                tenantId,
                () -> customerRepository
                        .findByIdAndTenantId(id, tenantId)
                        .map(customer -> {
                            customer.setName(request.name());
                            customer.setEmail(request.email());
                            customer.setPhone(request.phone());
                            Customer saved = customerRepository.save(customer);
                            return ResponseEntity.ok(CustomerResponse.from(saved));
                        })
                        .orElseGet(() -> ResponseEntity.notFound().build()));
    }
}
