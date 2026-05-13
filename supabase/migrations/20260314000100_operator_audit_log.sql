create table if not exists operator_audit_log (
  id bigserial primary key,
  event_type text not null,
  tx_id text,
  intent_hash varchar(12),
  match_id text,
  status text,
  sender_wallet text,
  amount_prizm numeric(14,2) default 0,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz default (now() at time zone 'utc')
);

create index if not exists idx_operator_audit_log_created_at
  on operator_audit_log (created_at desc);

create index if not exists idx_operator_audit_log_tx_id
  on operator_audit_log (tx_id);

create index if not exists idx_operator_audit_log_status
  on operator_audit_log (status);
