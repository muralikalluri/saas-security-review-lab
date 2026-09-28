package com.ledgerlite.tenantapi.config;

import com.ledgerlite.tenantapi.tenant.TenantContext;
import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class ApiExceptionHandler {

    @ExceptionHandler(TenantContext.MissingTenantClaimException.class)
    public ResponseEntity<Map<String, String>> handleMissingTenant(TenantContext.MissingTenantClaimException ex) {
        return ResponseEntity.status(HttpStatus.FORBIDDEN).body(Map.of("error", "missing_tenant_claim"));
    }

    @ExceptionHandler(CrossTenantReferenceException.class)
    public ResponseEntity<Map<String, String>> handleCrossTenantReference(CrossTenantReferenceException ex) {
        return ResponseEntity.status(HttpStatus.BAD_REQUEST).body(Map.of("error", ex.getMessage()));
    }
}
