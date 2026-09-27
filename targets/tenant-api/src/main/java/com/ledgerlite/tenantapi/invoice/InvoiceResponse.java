package com.ledgerlite.tenantapi.invoice;

import java.math.BigDecimal;

/**
 * A-03 (seeded flaw, SPEC.md A-03 / BOPLA): exposes {@code tenantId} and the
 * internal {@code internalCost} margin figure to API clients. A real DTO
 * for this endpoint should only ever return amount/status/customerId.
 */
public record InvoiceResponse(
        Long id, String tenantId, Long customerId, BigDecimal amount, BigDecimal internalCost, String status) {

    public static InvoiceResponse from(Invoice invoice) {
        return new InvoiceResponse(
                invoice.getId(),
                invoice.getTenantId(),
                invoice.getCustomerId(),
                invoice.getAmount(),
                invoice.getInternalCost(),
                invoice.getStatus());
    }
}
