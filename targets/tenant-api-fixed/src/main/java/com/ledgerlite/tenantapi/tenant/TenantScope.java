package com.ledgerlite.tenantapi.tenant;

import jakarta.persistence.EntityManager;
import java.util.function.Supplier;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Postgres RLS (defence in depth, SPEC.md "Fixed mode" line) enforcement
 * point. Every table with tenant-scoped rows (customers, invoices,
 * invites) has a row-level-security policy comparing {@code tenant_id} to
 * {@code current_setting('app.tenant_id', true)}. That session variable
 * MUST be set with {@code set_config(..., true)} - the "is_local" flag -
 * inside the SAME transaction that runs the query, otherwise it either
 * doesn't apply at all, or (worse, on a pooled connection) leaks into a
 * later, unrelated request that reuses the same physical connection.
 *
 * {@link #call} opens exactly one transaction, sets the session variable
 * as its first statement, and only then invokes the supplied action -
 * every repository call made inside that action joins this same
 * transaction (Spring's default REQUIRED propagation) and therefore the
 * same Postgres session, so the setting is guaranteed to be in effect.
 * The app's own datasource role has NO ownership of these tables (see
 * V3__row_level_security.sql) and RLS is not FORCE'd, so this is the ONLY
 * path by which the app can see any tenant-scoped row - forgetting to go
 * through this class fails closed (an empty result), never open.
 */
@Service
public class TenantScope {

    private final EntityManager entityManager;

    public TenantScope(EntityManager entityManager) {
        this.entityManager = entityManager;
    }

    @Transactional
    public <T> T call(String tenantId, Supplier<T> action) {
        applySessionTenant(tenantId);
        return action.get();
    }

    @Transactional
    public void run(String tenantId, Runnable action) {
        applySessionTenant(tenantId);
        action.run();
    }

    private void applySessionTenant(String tenantId) {
        entityManager
                .createNativeQuery("select set_config('app.tenant_id', :tenantId, true)")
                .setParameter("tenantId", tenantId)
                .getSingleResult();
    }
}
