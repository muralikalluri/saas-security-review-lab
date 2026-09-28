-- Fixed mode: Postgres RLS as defence in depth, on top of the explicit
-- WHERE tenant_id filters in the application code (which are what
-- actually close A-01/A-02/A-04/A-05/A-06 - see the Java changes).
--
-- This migration runs as the table-owning role (POSTGRES_USER, e.g.
-- ledgerlite_dev - see spring.flyway.* in application.yml, which point
-- Flyway at that role while the APPLICATION connects as a separate,
-- unprivileged role below). Table owners bypass RLS by default, which is
-- exactly what we want for Flyway/seeding; RLS is not FORCE'd, so only
-- non-owner roles are restricted.
--
-- app.tenant_id is set per-transaction via set_config(..., true) in
-- TenantScope.java - never a plain SET, which would leak across a pooled
-- connection's next, unrelated request. current_setting(..., true)
-- (missing_ok) returns NULL when unset, and `tenant_id = NULL` is never
-- true, so forgetting to go through TenantScope fails CLOSED (empty
-- result), not open.
--
-- A-09 fix: ${app_db_password} is a Flyway placeholder (see
-- spring.flyway.placeholders.app_db_password in application.yml) -
-- substituted from the SAME env var the app itself connects with
-- (DB_PASSWORD), never a literal committed here.

do $$
begin
    if not exists (select from pg_roles where rolname = 'ledgerlite_app') then
        create role ledgerlite_app login password '${app_db_password}';
    end if;
end
$$;

grant usage on schema public to ledgerlite_app;
grant select, insert, update, delete on customers, invoices, invites to ledgerlite_app;
grant usage, select on customers_id_seq, invoices_id_seq, invites_id_seq to ledgerlite_app;

alter table customers enable row level security;
alter table invoices enable row level security;
alter table invites enable row level security;

create policy tenant_isolation_customers on customers
    using (tenant_id = current_setting('app.tenant_id', true));

create policy tenant_isolation_invoices on invoices
    using (tenant_id = current_setting('app.tenant_id', true));

create policy tenant_isolation_invites on invites
    using (tenant_id = current_setting('app.tenant_id', true));
