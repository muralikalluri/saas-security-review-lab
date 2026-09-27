package com.ledgerlite.tenantapi.invoice;

import java.math.BigDecimal;
import java.util.List;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

/**
 * A-12 (seeded flaw, SPEC.md A-12): the `sort` query parameter is
 * concatenated directly into the SQL string instead of being validated
 * against a whitelist of column names, enabling SQL injection via the
 * ORDER BY clause. The tenant filter itself is still parameterised, so
 * this does NOT leak cross-tenant rows (see A-04/A-06 for those) - it is a
 * pure injection finding.
 */
@Repository
public class InvoiceSearchRepository {

    private final JdbcTemplate jdbcTemplate;

    public InvoiceSearchRepository(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    public List<InvoiceRow> searchByTenant(String tenantId, String sort) {
        String sql = "select id, tenant_id, customer_id, amount, internal_cost, status "
                + "from invoices where tenant_id = ? order by " + sort;
        return jdbcTemplate.query(
                sql,
                (rs, rowNum) -> new InvoiceRow(
                        rs.getLong("id"),
                        rs.getString("tenant_id"),
                        rs.getLong("customer_id"),
                        rs.getBigDecimal("amount"),
                        rs.getBigDecimal("internal_cost"),
                        rs.getString("status")),
                tenantId);
    }

    public record InvoiceRow(
            Long id, String tenantId, Long customerId, BigDecimal amount, BigDecimal internalCost, String status) {
    }
}
