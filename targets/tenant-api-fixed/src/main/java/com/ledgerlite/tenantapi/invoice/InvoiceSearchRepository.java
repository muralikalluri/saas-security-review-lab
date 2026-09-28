package com.ledgerlite.tenantapi.invoice;

import java.math.BigDecimal;
import java.util.List;
import java.util.Set;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.http.HttpStatus;

/**
 * A-12 fix: {@code sort} is validated against a whitelist of real column
 * names before being placed in the ORDER BY clause - never concatenated
 * from raw client input. Anything else is a 400, not a query.
 *
 * A-03 fix (BOPLA half): {@link InvoiceRow} drops tenantId/internalCost,
 * matching {@link InvoiceResponse}.
 */
@Repository
public class InvoiceSearchRepository {

    private static final Set<String> ALLOWED_SORT_COLUMNS = Set.of("id", "amount", "status", "created_at");

    private final JdbcTemplate jdbcTemplate;

    public InvoiceSearchRepository(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    public List<InvoiceRow> searchByTenant(String tenantId, String sort) {
        if (!ALLOWED_SORT_COLUMNS.contains(sort)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "sort must be one of " + ALLOWED_SORT_COLUMNS);
        }
        String sql = "select id, customer_id, amount, status from invoices where tenant_id = ? order by " + sort;
        return jdbcTemplate.query(
                sql,
                (rs, rowNum) -> new InvoiceRow(
                        rs.getLong("id"), rs.getLong("customer_id"), rs.getBigDecimal("amount"), rs.getString("status")),
                tenantId);
    }

    public record InvoiceRow(Long id, Long customerId, BigDecimal amount, String status) {
    }
}
