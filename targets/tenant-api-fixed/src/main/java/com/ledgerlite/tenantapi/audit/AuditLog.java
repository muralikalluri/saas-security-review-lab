package com.ledgerlite.tenantapi.audit;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.OffsetDateTime;

/** A-11 fix: role changes (invites) and exports are now audited, in the same transaction as the action itself. */
@Entity
@Table(name = "audit_log")
public class AuditLog {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "tenant_id", nullable = false)
    private String tenantId;

    @Column(nullable = false)
    private String actor;

    @Column(nullable = false)
    private String action;

    private String target;

    @Column(name = "created_at")
    private OffsetDateTime createdAt;

    protected AuditLog() {
    }

    public AuditLog(String tenantId, String actor, String action, String target) {
        this.tenantId = tenantId;
        this.actor = actor;
        this.action = action;
        this.target = target;
        this.createdAt = OffsetDateTime.now();
    }

    public Long getId() {
        return id;
    }
}
