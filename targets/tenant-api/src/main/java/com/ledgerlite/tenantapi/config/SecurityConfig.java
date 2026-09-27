package com.ledgerlite.tenantapi.config;

import java.util.Collection;
import java.util.List;
import java.util.stream.Collectors;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.authentication.AbstractAuthenticationToken;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationConverter;
import org.springframework.security.oauth2.server.resource.authentication.JwtGrantedAuthoritiesConverter;
import org.springframework.security.web.SecurityFilterChain;

/**
 * A-07 (seeded flaw, SPEC.md A-07): this is the ONLY authorization rule in
 * the baseline app - every endpoint under /invoices, /customers,
 * /dashboard, /users, /webhooks requires nothing more than a valid,
 * authenticated JWT. There is no per-endpoint role check
 * ({@code @PreAuthorize} / {@code hasRole(...)}) anywhere, so
 * {@code POST /users/invite} (and every other business endpoint) is
 * reachable by the lowest role, {@code viewer}, even though the product's
 * UI only shows that action to owner/admin.
 *
 * A-08 (seeded flaw, SPEC.md A-08): the JWT decoder is built from
 * {@code jwk-set-uri} only (see application.yml) - no issuer validator, no
 * audience validator is added below or anywhere else in this app.
 */
@Configuration
@EnableWebSecurity
public class SecurityConfig {

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http.csrf(AbstractHttpConfigurer::disable)
                .authorizeHttpRequests(auth -> auth
                        .requestMatchers("/actuator/health", "/api/status", "/auth/login")
                        .permitAll()
                        .anyRequest()
                        .authenticated())
                .oauth2ResourceServer(oauth2 -> oauth2.jwt(jwt -> jwt.jwtAuthenticationConverter(jwtAuthConverter())));
        return http.build();
    }

    private org.springframework.core.convert.converter.Converter<Jwt, AbstractAuthenticationToken> jwtAuthConverter() {
        JwtAuthenticationConverter converter = new JwtAuthenticationConverter();
        converter.setJwtGrantedAuthoritiesConverter(new RealmRoleConverter());
        return converter;
    }

    /** Maps Keycloak's {@code realm_access.roles} claim to Spring authorities, e.g. {@code ROLE_owner}. */
    static class RealmRoleConverter implements org.springframework.core.convert.converter.Converter<Jwt, Collection<GrantedAuthority>> {
        private final JwtGrantedAuthoritiesConverter defaultConverter = new JwtGrantedAuthoritiesConverter();

        @Override
        public Collection<GrantedAuthority> convert(Jwt jwt) {
            Collection<GrantedAuthority> authorities = defaultConverter.convert(jwt) == null
                    ? new java.util.ArrayList<>()
                    : new java.util.ArrayList<>(defaultConverter.convert(jwt));
            Object realmAccess = jwt.getClaims().get("realm_access");
            if (realmAccess instanceof java.util.Map<?, ?> map && map.get("roles") instanceof List<?> roles) {
                authorities.addAll(roles.stream()
                        .map(role -> new SimpleGrantedAuthority("ROLE_" + role))
                        .collect(Collectors.toList()));
            }
            return authorities;
        }
    }
}
