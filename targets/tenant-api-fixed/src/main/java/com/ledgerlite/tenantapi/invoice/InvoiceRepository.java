package com.ledgerlite.tenantapi.invoice;

import java.math.BigDecimal;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface InvoiceRepository extends JpaRepository<Invoice, Long> {

    List<Invoice> findByTenantId(String tenantId);

    /** A-01 fix: explicit WHERE tenant_id, not just "load by id". */
    Optional<Invoice> findByIdAndTenantId(Long id, String tenantId);

    @Query(value = "select coalesce(sum(amount), 0) from invoices where tenant_id = :tenantId", nativeQuery = true)
    BigDecimal sumAmountByTenantId(@Param("tenantId") String tenantId);
}
