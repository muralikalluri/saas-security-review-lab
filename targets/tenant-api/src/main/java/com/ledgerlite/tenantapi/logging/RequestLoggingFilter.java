package com.ledgerlite.tenantapi.logging;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

/**
 * A-11 (seeded flaw, SPEC.md A-11): logs the full, unredacted
 * {@code Authorization} header - including the raw bearer JWT - for every
 * request. Anyone with read access to application logs (a log aggregator,
 * a support engineer, a misconfigured log-shipping sink) can lift a live
 * token and replay it until it expires (see A-08 for how long that is).
 */
@Component
public class RequestLoggingFilter extends OncePerRequestFilter {

    private static final Logger log = LoggerFactory.getLogger(RequestLoggingFilter.class);

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        String authHeader = request.getHeader("Authorization");
        if (authHeader != null) {
            log.info("{} {} Authorization={}", request.getMethod(), request.getRequestURI(), authHeader);
        } else {
            log.info("{} {}", request.getMethod(), request.getRequestURI());
        }
        chain.doFilter(request, response);
    }
}
