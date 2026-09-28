package com.ledgerlite.tenantapi.invite;

import com.ledgerlite.tenantapi.audit.AuditLog;
import com.ledgerlite.tenantapi.audit.AuditLogRepository;
import com.ledgerlite.tenantapi.tenant.TenantContext;
import com.ledgerlite.tenantapi.tenant.TenantScope;
import jakarta.validation.Valid;
import java.util.Set;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * A-07 fix: only owner/admin may call this endpoint at all
 * ({@code @PreAuthorize}). Granting `owner` itself is rejected - an admin
 * should not be able to mint a new owner (not itself a numbered SPEC
 * finding, but the same class of privilege-escalation bug as A-07).
 *
 * A-11 fix: the invite is written in the same transaction as an
 * audit_log row.
 */
@RestController
@RequestMapping("/users")
public class InviteController {

    private static final Set<String> GRANTABLE_ROLES = Set.of("admin", "accountant", "viewer");

    private final InviteRepository inviteRepository;
    private final AuditLogRepository auditLogRepository;
    private final TenantContext tenantContext;
    private final TenantScope tenantScope;

    public InviteController(
            InviteRepository inviteRepository,
            AuditLogRepository auditLogRepository,
            TenantContext tenantContext,
            TenantScope tenantScope) {
        this.inviteRepository = inviteRepository;
        this.auditLogRepository = auditLogRepository;
        this.tenantContext = tenantContext;
        this.tenantScope = tenantScope;
    }

    @PreAuthorize("hasAnyRole('owner','admin')")
    @PostMapping("/invite")
    public ResponseEntity<?> invite(@Valid @RequestBody InviteRequest request) {
        if (!GRANTABLE_ROLES.contains(request.role())) {
            return ResponseEntity.status(HttpStatus.BAD_REQUEST).body("role must be one of " + GRANTABLE_ROLES);
        }
        String tenantId = tenantContext.tokenTenantId();
        String invitedBy = tenantContext.currentUsername();
        Long id = tenantScope.call(tenantId, () -> {
            Invite invite = new Invite(tenantId, request.email(), request.role(), invitedBy);
            Invite saved = inviteRepository.save(invite);
            auditLogRepository.save(new AuditLog(tenantId, invitedBy, "user.invite", request.email() + ":" + request.role()));
            return saved.getId();
        });
        return ResponseEntity.ok(id);
    }
}
