package com.ledgerlite.tenantapi.tenant;

import jakarta.servlet.http.HttpServletRequest;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;
import org.springframework.stereotype.Component;
import org.springframework.web.context.annotation.RequestScope;

/**
 * Resolves the "active tenant" for the current request.
 *
 * A-04 (seeded flaw, SPEC.md A-04): when the client sends an
 * {@code X-Tenant-Id} header, it wins over the tenant_id claim in the
 * caller's own JWT. Any authenticated user of tenant X can read tenant Y's
 * data through every endpoint that consults this context by simply sending
 * {@code X-Tenant-Id: <tenant Y>}. This is used ONLY by list/aggregate
 * endpoints (GET /invoices, GET /customers, GET /dashboard/summary) -
 * single-resource lookups by id (A-01 GET /invoices/{id}, A-02 PUT
 * /customers/{id}) intentionally do NOT go through this class at all, so
 * fixing this header-spoof bug in M3 will not also fix those.
 */
@Component
@RequestScope
public class TenantContext {

    public static final String TENANT_HEADER = "X-Tenant-Id";

    private final HttpServletRequest request;

    public TenantContext(HttpServletRequest request) {
        this.request = request;
    }

    public String currentTenantId() {
        String headerTenant = request.getHeader(TENANT_HEADER);
        if (headerTenant != null && !headerTenant.isBlank()) {
            return headerTenant;
        }
        return tokenTenantId();
    }

    public String tokenTenantId() {
        Object principal = SecurityContextHolder.getContext().getAuthentication();
        if (principal instanceof JwtAuthenticationToken jwtAuth) {
            Jwt jwt = jwtAuth.getToken();
            return jwt.getClaimAsString("tenant_id");
        }
        throw new IllegalStateException("No authenticated JWT principal in security context");
    }
}
