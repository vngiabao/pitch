PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS sources(
 id TEXT PRIMARY KEY, original_path TEXT NOT NULL UNIQUE, kind TEXT NOT NULL,
 classification TEXT NOT NULL, registered_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS source_versions(
 id TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES sources(id),
 sha256 TEXT NOT NULL, size_bytes INTEGER NOT NULL, captured_at TEXT NOT NULL,
 document_date TEXT, last_verified_at TEXT, body TEXT, extraction TEXT NOT NULL,
 UNIQUE(source_id,sha256)
);
CREATE TABLE IF NOT EXISTS imports(
 id TEXT PRIMARY KEY, source_version_id TEXT NOT NULL REFERENCES source_versions(id),
 destination_type TEXT NOT NULL, destination_id TEXT NOT NULL, locator TEXT NOT NULL,
 transformation TEXT NOT NULL, imported_at TEXT NOT NULL,
 UNIQUE(source_version_id,destination_type,destination_id)
);
CREATE TABLE IF NOT EXISTS claims(
 id TEXT PRIMARY KEY, topic TEXT NOT NULL, label TEXT NOT NULL,
 canonical_version_id TEXT REFERENCES claim_versions(id)
);
CREATE TABLE IF NOT EXISTS claim_versions(
 id TEXT PRIMARY KEY, claim_id TEXT NOT NULL REFERENCES claims(id), body TEXT NOT NULL,
 evidence_status TEXT NOT NULL CHECK(evidence_status IN ('reported','hypothesis','model','target','unknown','verified')),
 source_version_id TEXT NOT NULL REFERENCES source_versions(id), locator TEXT NOT NULL,
 last_verified_at TEXT, valid_until TEXT, created_at TEXT NOT NULL,
 supersedes TEXT REFERENCES claim_versions(id)
);
CREATE TABLE IF NOT EXISTS claim_reviews(
 version_id TEXT PRIMARY KEY REFERENCES claim_versions(id), status TEXT NOT NULL DEFAULT 'proposed'
 CHECK(status IN ('proposed','approved','rejected')), approval_id TEXT
);
CREATE TABLE IF NOT EXISTS opportunities(
 id TEXT PRIMARY KEY, dedup_key TEXT NOT NULL UNIQUE, organizer TEXT NOT NULL,
 program TEXT NOT NULL, cycle TEXT NOT NULL, official_url TEXT, deadline TEXT,
 deadline_timezone TEXT, terms_json TEXT NOT NULL, eligibility TEXT NOT NULL,
 fit_score REAL, fit_reason TEXT NOT NULL, state TEXT NOT NULL,
 last_checked_at TEXT, source_version_id TEXT REFERENCES source_versions(id)
);
CREATE TABLE IF NOT EXISTS applications(
 id TEXT PRIMARY KEY, opportunity_id TEXT NOT NULL REFERENCES opportunities(id),
 title TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'draft', created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS questions(
 id TEXT PRIMARY KEY, application_id TEXT NOT NULL REFERENCES applications(id),
 ordinal INTEGER NOT NULL, prompt TEXT NOT NULL, limit_value INTEGER,
 limit_unit TEXT CHECK(limit_unit IN ('characters','words') OR limit_unit IS NULL),
 required INTEGER NOT NULL DEFAULT 1, source_version_id TEXT NOT NULL REFERENCES source_versions(id),
 locator TEXT NOT NULL, checked INTEGER NOT NULL DEFAULT 0,
 UNIQUE(application_id,ordinal), CHECK(limit_value IS NULL OR limit_value>0)
);
CREATE TABLE IF NOT EXISTS answer_versions(
 id TEXT PRIMARY KEY, question_id TEXT NOT NULL REFERENCES questions(id), body TEXT NOT NULL,
 facts_json TEXT NOT NULL, sources_json TEXT NOT NULL, unresolved_json TEXT NOT NULL,
 created_at TEXT NOT NULL, supersedes TEXT REFERENCES answer_versions(id), provenance TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS answer_reviews(
 version_id TEXT PRIMARY KEY REFERENCES answer_versions(id), status TEXT NOT NULL DEFAULT 'draft'
 CHECK(status IN ('draft','approved','rejected')), approval_id TEXT
);
CREATE TABLE IF NOT EXISTS pitches(
 id TEXT PRIMARY KEY, duration_seconds INTEGER NOT NULL, audience TEXT NOT NULL,
 body TEXT NOT NULL, claim_versions_json TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'draft',
 created_at TEXT NOT NULL, source_version_id TEXT REFERENCES source_versions(id)
);
CREATE TABLE IF NOT EXISTS issues(
 id TEXT PRIMARY KEY, kind TEXT NOT NULL, title TEXT NOT NULL, detail TEXT NOT NULL,
 sources_json TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'open', created_at TEXT NOT NULL,
 UNIQUE(kind,title)
);
CREATE TABLE IF NOT EXISTS evidence(
 id TEXT PRIMARY KEY, kind TEXT NOT NULL, body TEXT NOT NULL,
 source_version_id TEXT NOT NULL REFERENCES source_versions(id), locator TEXT NOT NULL,
 permission_status TEXT NOT NULL, submission_id TEXT REFERENCES submissions(id), created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS approvals(
 id TEXT PRIMARY KEY, action TEXT NOT NULL, payload_json TEXT NOT NULL,
 payload_sha256 TEXT NOT NULL, expected_version TEXT,
 state TEXT NOT NULL DEFAULT 'pending' CHECK(state IN ('pending','approved','rejected')),
 requested_by TEXT NOT NULL, requested_at TEXT NOT NULL,
 decided_by TEXT, decided_at TEXT, decision_note TEXT
);
CREATE TABLE IF NOT EXISTS submissions(
 id TEXT PRIMARY KEY, application_id TEXT NOT NULL REFERENCES applications(id),
 submitted_at TEXT NOT NULL, receipt TEXT NOT NULL, payload_json TEXT NOT NULL,
 payload_sha256 TEXT NOT NULL, approval_id TEXT NOT NULL REFERENCES approvals(id), recorded_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS submission_blobs(sha256 TEXT PRIMARY KEY, content BLOB NOT NULL);
CREATE TABLE IF NOT EXISTS jobs(
 id TEXT PRIMARY KEY, capability TEXT NOT NULL, input_json TEXT NOT NULL,
 idempotency_key TEXT NOT NULL UNIQUE, state TEXT NOT NULL CHECK(state IN ('queued','running','complete','failed')),
 attempts INTEGER NOT NULL DEFAULT 0, max_attempts INTEGER NOT NULL DEFAULT 3,
 lease_until TEXT, result_json TEXT, error TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit(
 id INTEGER PRIMARY KEY AUTOINCREMENT, event TEXT NOT NULL, actor TEXT NOT NULL,
 payload_json TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS claim_topic ON claims(topic);
CREATE INDEX IF NOT EXISTS source_version_source ON source_versions(source_id);
CREATE INDEX IF NOT EXISTS jobs_status ON jobs(state,created_at);
CREATE TRIGGER IF NOT EXISTS immutable_claim_version BEFORE UPDATE ON claim_versions BEGIN SELECT RAISE(ABORT,'Claim versions are immutable'); END;
CREATE TRIGGER IF NOT EXISTS retain_claim_version BEFORE DELETE ON claim_versions BEGIN SELECT RAISE(ABORT,'Claim versions cannot be deleted'); END;
CREATE TRIGGER IF NOT EXISTS immutable_answer BEFORE UPDATE ON answer_versions BEGIN SELECT RAISE(ABORT,'Answer versions are immutable'); END;
CREATE TRIGGER IF NOT EXISTS retain_answer BEFORE DELETE ON answer_versions BEGIN SELECT RAISE(ABORT,'Answer versions cannot be deleted'); END;
CREATE TRIGGER IF NOT EXISTS immutable_submission BEFORE UPDATE ON submissions BEGIN SELECT RAISE(ABORT,'Submissions are immutable'); END;
CREATE TRIGGER IF NOT EXISTS retain_submission BEFORE DELETE ON submissions BEGIN SELECT RAISE(ABORT,'Submissions cannot be deleted'); END;
CREATE TRIGGER IF NOT EXISTS immutable_audit BEFORE UPDATE ON audit BEGIN SELECT RAISE(ABORT,'Audit is append only'); END;
CREATE TRIGGER IF NOT EXISTS retain_audit BEFORE DELETE ON audit BEGIN SELECT RAISE(ABORT,'Audit is append only'); END;
CREATE TRIGGER IF NOT EXISTS immutable_source_version BEFORE UPDATE ON source_versions BEGIN SELECT RAISE(ABORT,'Source versions are immutable'); END;
CREATE TRIGGER IF NOT EXISTS retain_source_version BEFORE DELETE ON source_versions BEGIN SELECT RAISE(ABORT,'Source versions cannot be deleted'); END;
CREATE TRIGGER IF NOT EXISTS immutable_submission_blob BEFORE UPDATE ON submission_blobs BEGIN SELECT RAISE(ABORT,'Submitted assets are immutable'); END;
CREATE TRIGGER IF NOT EXISTS retain_submission_blob BEFORE DELETE ON submission_blobs BEGIN SELECT RAISE(ABORT,'Submitted assets cannot be deleted'); END;
