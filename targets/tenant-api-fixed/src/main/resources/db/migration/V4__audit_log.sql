-- A-11 fix: role changes (invites) and exports are now audited.
create table audit_log (
    id bigserial primary key,
    tenant_id varchar(64) not null,
    actor varchar(255) not null,
    action varchar(64) not null,
    target varchar(255),
    created_at timestamptz not null default now()
);

create index idx_audit_log_tenant on audit_log(tenant_id);

grant select, insert on audit_log to ledgerlite_app;
grant usage, select on audit_log_id_seq to ledgerlite_app;

alter table audit_log enable row level security;

create policy tenant_isolation_audit_log on audit_log
    using (tenant_id = current_setting('app.tenant_id', true));
