package com.ledgerlite.tenantapi.invoice;

import java.math.BigDecimal;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface InvoiceRepository extends JpaRepository<Invoice, Long> {

    List<Invoice> findByTenantId(String tenantId);

    @Query(value = "select coalesce(sum(amount), 0) from invoices where tenant_id = :tenantId", nativeQuery = true)
    BigDecimal sumAmountByTenantId(@Param("tenantId") String tenantId);
}
