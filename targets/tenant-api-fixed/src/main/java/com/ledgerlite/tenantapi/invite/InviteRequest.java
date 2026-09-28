package com.ledgerlite.tenantapi.invite;

import jakarta.validation.constraints.NotBlank;

public record InviteRequest(@NotBlank String email, @NotBlank String role) {
}
