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
 * A-11 fix: never logs the Authorization header's value, only whether one
 * was present - no bearer token can be lifted from application logs.
 */
@Component
public class RequestLoggingFilter extends OncePerRequestFilter {

    private static final Logger log = LoggerFactory.getLogger(RequestLoggingFilter.class);

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        boolean authenticated = request.getHeader("Authorization") != null;
        log.info("{} {} authenticated={}", request.getMethod(), request.getRequestURI(), authenticated);
        chain.doFilter(request, response);
    }
}
