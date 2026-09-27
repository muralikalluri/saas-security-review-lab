package com.ledgerlite.tenantapi.invoice;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import java.math.BigDecimal;

/**
 * A-03 (seeded flaw, SPEC.md A-03): {@code tenantId} is bindable straight
 * from the client request body (mass assignment). The controller trusts it
 * instead of deriving the tenant from the caller's own JWT, so a caller in
 * tenant X can create rows that belong to tenant Y.
 */
public record InvoiceCreateRequest(
        String tenantId,
        @NotNull Long customerId,
        @NotNull BigDecimal amount,
        @NotNull BigDecimal internalCost,
        @NotBlank String status) {
}
