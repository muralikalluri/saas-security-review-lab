package com.ledgerlite.tenantapi.tenant;

import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;
import org.springframework.stereotype.Component;
import org.springframework.web.context.annotation.RequestScope;

/**
 * Resolves the "active tenant" for the current request.
 *
 * A-04 fix: the tenant is ALWAYS derived from the caller's own JWT
 * {@code tenant_id} claim. No request header of any kind is consulted -
 * there is no client-controlled input into this decision at all. A
 * request whose token is missing the claim is rejected outright rather
 * than falling back to anything.
 */
@Component
@RequestScope
public class TenantContext {

    public String currentTenantId() {
        return tokenTenantId();
    }

    public String tokenTenantId() {
        Object principal = SecurityContextHolder.getContext().getAuthentication();
        if (principal instanceof JwtAuthenticationToken jwtAuth) {
            Jwt jwt = jwtAuth.getToken();
            String tenantId = jwt.getClaimAsString("tenant_id");
            if (tenantId == null || tenantId.isBlank()) {
                throw new MissingTenantClaimException();
            }
            return tenantId;
        }
        throw new IllegalStateException("No authenticated JWT principal in security context");
    }

    public String currentUsername() {
        Object principal = SecurityContextHolder.getContext().getAuthentication();
        if (principal instanceof JwtAuthenticationToken jwtAuth) {
            String preferredUsername = jwtAuth.getToken().getClaimAsString("preferred_username");
            return preferredUsername != null ? preferredUsername : jwtAuth.getToken().getSubject();
        }
        return "unknown";
    }

    public static class MissingTenantClaimException extends RuntimeException {
        public MissingTenantClaimException() {
            super("JWT is missing the required tenant_id claim");
        }
    }
}
