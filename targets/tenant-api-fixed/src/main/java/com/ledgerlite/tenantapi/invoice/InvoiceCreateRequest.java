package com.ledgerlite.tenantapi.invoice;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import java.math.BigDecimal;

/**
 * A-03 fix: {@code tenantId} is no longer part of this DTO at all - there
 * is nothing for a client to mass-assign. The tenant is always derived
 * from the caller's own JWT (see InvoiceController).
 */
public record InvoiceCreateRequest(
        @NotNull Long customerId, @NotNull BigDecimal amount, @NotNull BigDecimal internalCost, @NotBlank String status) {
}
