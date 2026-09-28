package com.ledgerlite.tenantapi.config;

/** Thrown when a request references another tenant's resource by id (e.g. a customerId that doesn't belong to the caller). */
public class CrossTenantReferenceException extends RuntimeException {
    public CrossTenantReferenceException(String message) {
        super(message);
    }
}
