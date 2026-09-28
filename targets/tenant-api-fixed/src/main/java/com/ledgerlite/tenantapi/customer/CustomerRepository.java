package com.ledgerlite.tenantapi.customer;

import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface CustomerRepository extends JpaRepository<Customer, Long> {

    List<Customer> findByTenantId(String tenantId);

    /** A-02 fix: explicit WHERE tenant_id, not just "load by id". */
    Optional<Customer> findByIdAndTenantId(Long id, String tenantId);
}
