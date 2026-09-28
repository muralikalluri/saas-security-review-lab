package com.ledgerlite.tenantapi;

import org.junit.jupiter.api.extension.ExtendWith;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

/**
 * Base for tests that need a real Postgres (so Flyway migrations - INCLUDING
 * V3's RLS role/policy setup - run for real) but not a live Keycloak; JWTs
 * are simulated per-test with spring-security-test's
 * {@code SecurityMockMvcRequestPostProcessors.jwt()}.
 *
 * Two roles, matching the real docker-compose split (see TenantScope):
 * Flyway runs as the Testcontainers-provided admin user (table owner,
 * bypasses RLS, can CREATE ROLE); the app's own runtime datasource
 * connects as ledgerlite_app - the same restricted, RLS-bound role that
 * V3__row_level_security.sql creates with this exact password.
 */
@Testcontainers
@SpringBootTest
@AutoConfigureMockMvc
@ExtendWith(org.springframework.test.context.junit.jupiter.SpringExtension.class)
abstract class AbstractIntegrationTest {

    static final String APP_ROLE_PASSWORD = "apponly_local_dev_password_do_not_use";

    @Container
    static final PostgreSQLContainer<?> POSTGRES =
            new PostgreSQLContainer<>("postgres:16-alpine").withDatabaseName("ledgerlite_test");

    @DynamicPropertySource
    static void datasourceProperties(DynamicPropertyRegistry registry) {
        registry.add("spring.flyway.url", POSTGRES::getJdbcUrl);
        registry.add("spring.flyway.user", POSTGRES::getUsername);
        registry.add("spring.flyway.password", POSTGRES::getPassword);
        // Matches V3__row_level_security.sql's `${app_db_password}` placeholder.
        registry.add("spring.flyway.placeholders.app_db_password", () -> APP_ROLE_PASSWORD);

        registry.add("spring.datasource.url", POSTGRES::getJdbcUrl);
        registry.add("spring.datasource.username", () -> "ledgerlite_app");
        registry.add("spring.datasource.password", () -> APP_ROLE_PASSWORD);
    }
}
