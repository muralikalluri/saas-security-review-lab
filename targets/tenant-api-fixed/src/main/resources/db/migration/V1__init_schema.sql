-- Deliberately insecure for demonstration. Do not deploy.
-- Fixed-mode schema: same shared tables with a tenant_id column as the
-- baseline (this file is otherwise unchanged from it), but see
-- V3__row_level_security.sql for the RLS policies added on top, and the
-- application code (explicit WHERE tenant_id, via TenantScope) for the
-- actual A-01/A-02/A-04/A-05/A-06 fixes.

create table customers (
    id bigserial primary key,
    tenant_id varchar(64) not null,
    name varchar(255) not null,
    email varchar(255),
    phone varchar(64),
    created_at timestamptz not null default now()
);

create table invoices (
    id bigserial primary key,
    tenant_id varchar(64) not null,
    customer_id bigint not null references customers(id),
    amount numeric(12,2) not null,
    internal_cost numeric(12,2) not null,
    status varchar(32) not null default 'draft',
    created_at timestamptz not null default now()
);

create table invites (
    id bigserial primary key,
    tenant_id varchar(64) not null,
    email varchar(255) not null,
    role varchar(32) not null,
    invited_by varchar(255) not null,
    created_at timestamptz not null default now()
);

create index idx_customers_tenant on customers(tenant_id);
create index idx_invoices_tenant on invoices(tenant_id);
create index idx_invites_tenant on invites(tenant_id);
