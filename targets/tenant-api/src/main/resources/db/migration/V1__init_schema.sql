-- Deliberately insecure for demonstration. Do not deploy.
-- Baseline schema: shared tables with a tenant_id column and NO row-level
-- security, NO database-level tenant constraint. Isolation is meant to be
-- enforced entirely in application code, which is where A-01/A-02/A-04
-- fail to do so. See SPEC.md section 2.

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
