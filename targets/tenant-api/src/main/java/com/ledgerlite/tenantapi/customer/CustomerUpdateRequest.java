package com.ledgerlite.tenantapi.customer;

import jakarta.validation.constraints.NotBlank;

public record CustomerUpdateRequest(@NotBlank String name, String email, String phone) {
}
