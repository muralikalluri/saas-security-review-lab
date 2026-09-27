package com.ledgerlite.tenantapi.customer;

public record CustomerResponse(Long id, String tenantId, String name, String email, String phone) {

    public static CustomerResponse from(Customer customer) {
        return new CustomerResponse(
                customer.getId(),
                customer.getTenantId(),
                customer.getName(),
                customer.getEmail(),
                customer.getPhone());
    }
}
