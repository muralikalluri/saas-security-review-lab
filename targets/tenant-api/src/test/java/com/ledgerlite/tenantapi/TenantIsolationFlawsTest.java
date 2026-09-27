package com.ledgerlite.tenantapi;

import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.request.RequestPostProcessor;

/**
 * Proves the isolation-relevant seeded flaws (A-01, A-02, A-03, A-04, A-06,
 * A-07 - the ones SPEC.md §3 says the isolation-tester should also
 * rediscover generically) against the real Postgres/Flyway schema, using
 * simulated JWTs instead of a live Keycloak. A-05/A-08..A-13 are proven by
 * the curl scripts in exploits/ against the full docker-compose stack
 * instead (see exploits/README.md).
 */
class TenantIsolationFlawsTest extends AbstractIntegrationTest {

    private static final String ACME = "tenant-acme-001";
    private static final String GLOBEX = "tenant-globex-002";

    @Autowired
    private MockMvc mockMvc;

    private static RequestPostProcessor as(String tenantId, String role) {
        return jwt().jwt(jwt -> jwt.claim("tenant_id", tenantId).subject(role + "@" + tenantId))
                .authorities(new SimpleGrantedAuthority("ROLE_" + role));
    }

    @Test
    void a01_getInvoiceById_leaksAcrossTenants() throws Exception {
        // Invoice id 1 belongs to ACME (see V2__seed_data.sql). A Globex viewer can read it.
        mockMvc.perform(get("/invoices/1").with(as(GLOBEX, "viewer")))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.tenantId").value(ACME));
    }

    @Test
    void a02_updateCustomerById_overwritesAcrossTenants() throws Exception {
        // Customer id 1 belongs to ACME. A Globex owner can overwrite it.
        mockMvc.perform(put("/customers/1")
                        .with(as(GLOBEX, "owner"))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"name\":\"cross-tenant overwrite\",\"email\":\"x@example.invalid\",\"phone\":\"0\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.tenantId").value(ACME));
    }

    @Test
    void a03_createInvoice_massAssignsForeignTenantId() throws Exception {
        mockMvc.perform(post("/invoices")
                        .with(as(GLOBEX, "viewer"))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"tenantId\":\"" + ACME
                                + "\",\"customerId\":1,\"amount\":1.00,\"internalCost\":0.50,\"status\":\"draft\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.tenantId").value(ACME))
                .andExpect(jsonPath("$.internalCost").exists());
    }

    @Test
    void a04_listInvoices_headerOverridesTokenTenant() throws Exception {
        mockMvc.perform(get("/invoices").with(as(GLOBEX, "viewer")).header("X-Tenant-Id", ACME))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].tenantId").value(ACME));
    }

    @Test
    void a04Control_listInvoices_withoutHeaderStaysInOwnTenant() throws Exception {
        mockMvc.perform(get("/invoices").with(as(GLOBEX, "viewer")))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].tenantId").value(GLOBEX));
    }

    @Test
    void a06_dashboardSummary_cacheLeaksBetweenTenants() throws Exception {
        String acmeBody = mockMvc.perform(get("/dashboard/summary").with(as(ACME, "owner")))
                .andExpect(status().isOk())
                .andReturn()
                .getResponse()
                .getContentAsString();
        String globexBody = mockMvc.perform(get("/dashboard/summary").with(as(GLOBEX, "owner")))
                .andExpect(status().isOk())
                .andReturn()
                .getResponse()
                .getContentAsString();
        org.assertj.core.api.Assertions.assertThat(globexBody).isEqualTo(acmeBody);
    }

    @Test
    void a07_viewerCanCallUserInvite() throws Exception {
        mockMvc.perform(post("/users/invite")
                        .with(as(ACME, "viewer"))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"email\":\"new@acme-fictional.example\",\"role\":\"admin\"}"))
                .andExpect(status().isOk());
    }
}
