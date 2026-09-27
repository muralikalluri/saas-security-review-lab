package com.ledgerlite.tenantapi.customer;

import com.ledgerlite.tenantapi.tenant.TenantContext;
import jakarta.validation.Valid;
import java.util.List;
import org.springframework.http.ResponseEntity;
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

    public CustomerController(CustomerRepository customerRepository, TenantContext tenantContext) {
        this.customerRepository = customerRepository;
        this.tenantContext = tenantContext;
    }

    /**
     * A-04 (seeded flaw, SPEC.md A-04): scoped by {@link TenantContext#currentTenantId()},
     * which trusts the client-supplied X-Tenant-Id header over the JWT.
     */
    @GetMapping
    public List<CustomerResponse> list() {
        String tenantId = tenantContext.currentTenantId();
        return customerRepository.findByTenantId(tenantId).stream()
                .map(CustomerResponse::from)
                .toList();
    }

    @GetMapping("/{id}")
    public ResponseEntity<CustomerResponse> get(@PathVariable Long id) {
        String tenantId = tenantContext.tokenTenantId();
        return customerRepository.findById(id)
                .filter(c -> c.getTenantId().equals(tenantId))
                .map(c -> ResponseEntity.ok(CustomerResponse.from(c)))
                .orElseGet(() -> ResponseEntity.notFound().build());
    }

    /**
     * A-02 (seeded flaw, SPEC.md A-02): loads the customer purely by primary
     * key and saves the update with no tenant_id check at all - any
     * authenticated user of ANY tenant can rewrite another tenant's
     * customer record if they know (or enumerate) its id.
     */
    @PutMapping("/{id}")
    public ResponseEntity<CustomerResponse> update(
            @PathVariable Long id, @Valid @RequestBody CustomerUpdateRequest request) {
        return customerRepository.findById(id)
                .map(customer -> {
                    customer.setName(request.name());
                    customer.setEmail(request.email());
                    customer.setPhone(request.phone());
                    Customer saved = customerRepository.save(customer);
                    return ResponseEntity.ok(CustomerResponse.from(saved));
                })
                .orElseGet(() -> ResponseEntity.notFound().build());
    }
}
