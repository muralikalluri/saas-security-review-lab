package com.ledgerlite.tenantapi.invite;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.OffsetDateTime;

@Entity
@Table(name = "invites")
public class Invite {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "tenant_id", nullable = false)
    private String tenantId;

    @Column(nullable = false)
    private String email;

    @Column(nullable = false)
    private String role;

    @Column(name = "invited_by", nullable = false)
    private String invitedBy;

    @Column(name = "created_at")
    private OffsetDateTime createdAt;

    protected Invite() {
    }

    public Invite(String tenantId, String email, String role, String invitedBy) {
        this.tenantId = tenantId;
        this.email = email;
        this.role = role;
        this.invitedBy = invitedBy;
        this.createdAt = OffsetDateTime.now();
    }

    public Long getId() {
        return id;
    }

    public String getTenantId() {
        return tenantId;
    }

    public String getEmail() {
        return email;
    }

    public String getRole() {
        return role;
    }

    public String getInvitedBy() {
        return invitedBy;
    }
}
