package com.ledgerlite.tenantapi.invoice;

import java.math.BigDecimal;

/**
 * A-03 fix (BOPLA half): neither {@code tenantId} (an internal grouping
 * key, meaningless to a client already scoped to one tenant) nor
 * {@code internalCost} (a margin figure that should never leave the
 * backend) appear in this DTO.
 */
public record InvoiceResponse(Long id, Long customerId, BigDecimal amount, String status) {

    public static InvoiceResponse from(Invoice invoice) {
        return new InvoiceResponse(invoice.getId(), invoice.getCustomerId(), invoice.getAmount(), invoice.getStatus());
    }
}
