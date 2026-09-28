package com.ledgerlite.tenantapi;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.jayway.jsonpath.JsonPath;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.request.RequestPostProcessor;

/**
 * Proves the M3 fixes hold: every scenario TenantIsolationFlawsTest (M1
 * baseline) proved as a LEAK, this proves as DENIED/404/ignored - plus the
 * missing-tenant-claim and role-matrix invariants that only exist in
 * fixed mode. Same Testcontainers-Postgres + simulated-JWT approach as
 * the baseline module (see AbstractIntegrationTest), so no live Keycloak
 * is needed here either.
 */
class TenantIsolationFixedTest extends AbstractIntegrationTest {

    private static final String ACME = "tenant-acme-001";
    private static final String GLOBEX = "tenant-globex-002";

    @Autowired
    private MockMvc mockMvc;

    private static RequestPostProcessor as(String tenantId, String role) {
        return jwt().jwt(j -> j.claim("tenant_id", tenantId)
                        .claim("preferred_username", role + "@" + tenantId)
                        .subject(role + "@" + tenantId))
                .authorities(new SimpleGrantedAuthority("ROLE_" + role));
    }

    private static RequestPostProcessor withoutTenantClaim(String role) {
        return jwt().jwt(j -> j.subject(role).claim("no_tenant", true))
                .authorities(new SimpleGrantedAuthority("ROLE_" + role));
    }

    @Test
    void a01_getInvoiceById_foreignIdIs404() throws Exception {
        mockMvc.perform(get("/invoices/1").with(as(GLOBEX, "viewer"))).andExpect(status().isNotFound());
    }

    @Test
    void a01Control_getInvoiceById_ownIdIs200() throws Exception {
        mockMvc.perform(get("/invoices/1").with(as(ACME, "owner")))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value(1));
    }

    @Test
    void a02_updateCustomerById_foreignIdIs404AndDoesNotWrite() throws Exception {
        mockMvc.perform(put("/customers/1")
                        .with(as(GLOBEX, "owner"))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"name\":\"should not land\",\"email\":\"x@example.invalid\",\"phone\":\"0\"}"))
                .andExpect(status().isNotFound());

        mockMvc.perform(get("/customers/1").with(as(ACME, "owner")))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.name").value("Northwind Traders (fictional)"));
    }

    @Test
    void a03_createInvoice_tenantIdIgnoredAndResponseHasNoInternalFields() throws Exception {
        String body = mockMvc.perform(post("/invoices")
                        .with(as(GLOBEX, "owner"))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"tenantId\":\"" + ACME
                                + "\",\"customerId\":3,\"amount\":1.00,\"internalCost\":0.50,\"status\":\"draft\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.tenantId").doesNotExist())
                .andExpect(jsonPath("$.internalCost").doesNotExist())
                .andReturn()
                .getResponse()
                .getContentAsString();
        long createdId = JsonPath.<Number>read(body, "$.id").longValue();

        // The row must actually have landed in GLOBEX (the caller's real
        // tenant), never ACME (the injected tenantId) - visible to one,
        // invisible to the other.
        mockMvc.perform(get("/invoices/" + createdId).with(as(GLOBEX, "owner"))).andExpect(status().isOk());
        mockMvc.perform(get("/invoices/" + createdId).with(as(ACME, "owner"))).andExpect(status().isNotFound());
    }

    @Test
    void a03_createInvoice_crossTenantCustomerIdRejected() throws Exception {
        mockMvc.perform(post("/invoices")
                        .with(as(GLOBEX, "owner"))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"customerId\":1,\"amount\":1.00,\"internalCost\":0.50,\"status\":\"draft\"}"))
                .andExpect(status().isBadRequest());
    }

    @Test
    void a04_listInvoices_headerIsIgnored() throws Exception {
        String body = mockMvc.perform(get("/invoices").with(as(GLOBEX, "viewer")).header("X-Tenant-Id", ACME))
                .andExpect(status().isOk())
                .andReturn()
                .getResponse()
                .getContentAsString();
        java.util.List<Integer> ids = JsonPath.read(body, "$[*].id");
        assertThat(ids).contains(3, 4).doesNotContain(1, 2);
    }

    @Test
    void a05_exportDownload_foreignIdIs404() throws Exception {
        String createBody = mockMvc.perform(post("/invoices/export").with(as(ACME, "owner")))
                .andExpect(status().isOk())
                .andReturn()
                .getResponse()
                .getContentAsString();
        long exportId = com.jayway.jsonpath.JsonPath.<Number>read(createBody, "$.exportId").longValue();

        mockMvc.perform(get("/invoices/exports/" + exportId).with(as(GLOBEX, "owner"))).andExpect(status().isNotFound());
        mockMvc.perform(get("/invoices/exports/" + exportId).with(as(ACME, "owner"))).andExpect(status().isOk());
    }

    @Test
    void a06_dashboardSummary_isolatedRegardlessOfOrder() throws Exception {
        // Compare only totalAmount, never the whole body - "source" (computed
        // vs cache) legitimately differs between the first and second call to
        // the SAME tenant's own key, without that being a leak.
        double acmeTotal = dashboardTotal(ACME);
        double globexTotal = dashboardTotal(GLOBEX);
        assertThat(acmeTotal).isNotEqualTo(globexTotal);

        // reverse order, and a second call to globex's own key (now cached) -
        // must still be correct, not just "whoever asks first wins".
        double globexAgain = dashboardTotal(GLOBEX);
        assertThat(globexAgain).isEqualTo(globexTotal);
    }

    private double dashboardTotal(String tenantId) throws Exception {
        String body = mockMvc.perform(get("/dashboard/summary").with(as(tenantId, "owner")))
                .andExpect(status().isOk())
                .andReturn()
                .getResponse()
                .getContentAsString();
        return JsonPath.<Number>read(body, "$.totalAmount").doubleValue();
    }

    @Test
    void a07_viewerCannotInvite() throws Exception {
        mockMvc.perform(post("/users/invite")
                        .with(as(ACME, "viewer"))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"email\":\"new@acme-fictional.example\",\"role\":\"admin\"}"))
                .andExpect(status().isForbidden());
    }

    @Test
    void a07_adminCannotGrantOwnerRole() throws Exception {
        mockMvc.perform(post("/users/invite")
                        .with(as(ACME, "admin"))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"email\":\"new@acme-fictional.example\",\"role\":\"owner\"}"))
                .andExpect(status().isBadRequest());
    }

    @Test
    void a07_adminCanInvite() throws Exception {
        mockMvc.perform(post("/users/invite")
                        .with(as(ACME, "admin"))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"email\":\"new@acme-fictional.example\",\"role\":\"accountant\"}"))
                .andExpect(status().isOk());
    }

    @Test
    void missingTenantClaim_isForbidden() throws Exception {
        mockMvc.perform(get("/invoices").with(withoutTenantClaim("owner"))).andExpect(status().isForbidden());
    }
}
