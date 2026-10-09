CREATE TABLE IF NOT EXISTS autonomy_authorizations(
 id TEXT PRIMARY KEY, scope TEXT NOT NULL, payload_json TEXT NOT NULL,
 payload_sha256 TEXT NOT NULL, granted_at TEXT NOT NULL, revoked_at TEXT,
 owner_instruction TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS application_plans(
 id TEXT PRIMARY KEY, opportunity_id TEXT NOT NULL UNIQUE REFERENCES opportunities(id),
 application_id TEXT NOT NULL REFERENCES applications(id), state TEXT NOT NULL,
 selected_email TEXT NOT NULL, payload_json TEXT NOT NULL, blockers_json TEXT NOT NULL,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS application_adapters(
 opportunity_id TEXT PRIMARY KEY REFERENCES opportunities(id), definition_json TEXT NOT NULL,
 fingerprint TEXT NOT NULL, checked_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS application_attempts(
 id TEXT PRIMARY KEY, plan_id TEXT NOT NULL REFERENCES application_plans(id),
 payload_sha256 TEXT NOT NULL, state TEXT NOT NULL, started_at TEXT NOT NULL,
 completed_at TEXT, receipt_json TEXT, error TEXT,
 UNIQUE(plan_id,payload_sha256)
);
CREATE TABLE IF NOT EXISTS daily_reports(
 id TEXT PRIMARY KEY, local_date TEXT NOT NULL UNIQUE, recipient TEXT NOT NULL,
 subject TEXT NOT NULL, body TEXT NOT NULL, state TEXT NOT NULL,
 created_at TEXT NOT NULL, sent_at TEXT, receipt_json TEXT, error TEXT
);
CREATE TABLE IF NOT EXISTS application_confirmations(
 id TEXT PRIMARY KEY, plan_id TEXT NOT NULL REFERENCES application_plans(id),
 payload_json TEXT NOT NULL, payload_sha256 TEXT NOT NULL,
 email_json TEXT NOT NULL, email_state TEXT NOT NULL, email_receipt_json TEXT,
 decision TEXT NOT NULL DEFAULT 'PENDING', decided_at TEXT, created_at TEXT NOT NULL,
 UNIQUE(plan_id,payload_sha256)
);
CREATE TABLE IF NOT EXISTS opportunity_supersessions(
 superseded_id TEXT PRIMARY KEY REFERENCES opportunities(id),
 current_id TEXT NOT NULL REFERENCES opportunities(id), reason TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TRIGGER IF NOT EXISTS application_preview_immutable BEFORE UPDATE OF plan_id,payload_json,payload_sha256,email_json,created_at ON application_confirmations
 BEGIN SELECT RAISE(ABORT,'Application preview is immutable'); END;
CREATE TRIGGER IF NOT EXISTS autonomy_scope_immutable BEFORE UPDATE OF scope,payload_json,payload_sha256,granted_at,owner_instruction ON autonomy_authorizations
 BEGIN SELECT RAISE(ABORT,'Owner authorization is immutable; revoke and replace'); END;
CREATE TRIGGER IF NOT EXISTS autonomy_scope_retain BEFORE DELETE ON autonomy_authorizations
 BEGIN SELECT RAISE(ABORT,'Owner authorization must be retained'); END;
