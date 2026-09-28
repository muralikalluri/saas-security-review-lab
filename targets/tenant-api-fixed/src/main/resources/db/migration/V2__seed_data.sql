-- Deliberately insecure for demonstration. Do not deploy.
-- Fictional seed data for two tenants, matching the tenant_id values baked
-- into targets/tenant-api/keycloak/ledgerlite-realm.json so exploit scripts
-- and the isolation tester have stable, known ids to target.
-- Tenant 1 = tenant-acme-001 ("Acme Fictional Co"), users alice/bob/carol/dave.
-- Tenant 2 = tenant-globex-002 ("Globex Fictional Inc"), users erin/frank.

insert into customers (id, tenant_id, name, email, phone) values
    (1, 'tenant-acme-001', 'Northwind Traders (fictional)', 'ap@northwind-fictional.example', '+1-555-0101'),
    (2, 'tenant-acme-001', 'Southgate Retail (fictional)', 'ap@southgate-fictional.example', '+1-555-0102'),
    (3, 'tenant-globex-002', 'Wayfarer Logistics (fictional)', 'ap@wayfarer-fictional.example', '+1-555-0201'),
    (4, 'tenant-globex-002', 'Bluecrest Media (fictional)', 'ap@bluecrest-fictional.example', '+1-555-0202');

insert into invoices (id, tenant_id, customer_id, amount, internal_cost, status) values
    (1, 'tenant-acme-001', 1, 1200.00, 450.00, 'sent'),
    (2, 'tenant-acme-001', 2, 3400.00, 1100.00, 'paid'),
    (3, 'tenant-globex-002', 3, 5600.00, 2200.00, 'sent'),
    (4, 'tenant-globex-002', 4, 900.00, 300.00, 'draft');

select setval('customers_id_seq', (select max(id) from customers));
select setval('invoices_id_seq', (select max(id) from invoices));
