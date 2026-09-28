package com.ledgerlite.tenantapi.webhook;

import jakarta.validation.constraints.NotBlank;

public record WebhookTestRequest(@NotBlank String url) {
}
