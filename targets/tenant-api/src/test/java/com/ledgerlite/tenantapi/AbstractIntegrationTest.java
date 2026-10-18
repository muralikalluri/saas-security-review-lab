package com.ledgerlite.tenantapi;

import org.junit.jupiter.api.extension.ExtendWith;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.testcontainers.containers.PostgreSQLContainer;

/**
 * Base for tests that need a real Postgres (so Flyway migrations run for
 * real) but not a live Keycloak - JWTs are simulated per-test with
 * spring-security-test's {@code SecurityMockMvcRequestPostProcessors.jwt()}.
 */
@SpringBootTest
@AutoConfigureMockMvc
@ExtendWith(org.springframework.test.context.junit.jupiter.SpringExtension.class)
abstract class AbstractIntegrationTest {

    // Singleton container: started once per JVM and shared by every test class.
    // Not a JUnit-managed @Container, because that is stopped after each class
    // while Spring caches the application context (and its connection pool)
    // across classes - the second class would then talk to a dead Postgres.
    static final PostgreSQLContainer<?> POSTGRES =
            new PostgreSQLContainer<>("postgres:16-alpine").withDatabaseName("ledgerlite_test");

    static {
        POSTGRES.start();
    }

    @DynamicPropertySource
    static void datasourceProperties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", POSTGRES::getJdbcUrl);
        registry.add("spring.datasource.username", POSTGRES::getUsername);
        registry.add("spring.datasource.password", POSTGRES::getPassword);
    }
}
