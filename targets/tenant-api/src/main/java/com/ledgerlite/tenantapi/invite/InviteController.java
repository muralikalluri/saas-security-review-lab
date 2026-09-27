package com.ledgerlite.tenantapi.invite;

import com.ledgerlite.tenantapi.tenant.TenantContext;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * A-07 (seeded flaw, SPEC.md A-07 / BFLA): this endpoint has no
 * {@code @PreAuthorize} and no role check of any kind - it only requires
 * the caller to be authenticated (see SecurityConfig). The product's UI
 * hides the "Invite" button from the `viewer` role, but the API happily
 * accepts the request from any role in the tenant.
 *
 * A-11 (seeded flaw, SPEC.md A-11): this role-granting action is not
 * written to any audit trail - there is no audit table in the baseline.
 */
@RestController
@RequestMapping("/users")
public class InviteController {

    private final InviteRepository inviteRepository;
    private final TenantContext tenantContext;

    public InviteController(InviteRepository inviteRepository, TenantContext tenantContext) {
        this.inviteRepository = inviteRepository;
        this.tenantContext = tenantContext;
    }

    @PostMapping("/invite")
    public ResponseEntity<Long> invite(@Valid @RequestBody InviteRequest request) {
        String tenantId = tenantContext.tokenTenantId();
        String invitedBy = currentUsername();
        Invite invite = new Invite(tenantId, request.email(), request.role(), invitedBy);
        Invite saved = inviteRepository.save(invite);
        // A-11: no corresponding audit_log write here - intentional.
        return ResponseEntity.ok(saved.getId());
    }

    private String currentUsername() {
        var auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth instanceof JwtAuthenticationToken jwtAuth) {
            return jwtAuth.getToken().getSubject();
        }
        return "unknown";
    }
}
