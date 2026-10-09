CREATE TABLE IF NOT EXISTS funding_programs(
 id TEXT PRIMARY KEY, canonical_name TEXT NOT NULL, organizer TEXT NOT NULL,
 identity_key TEXT NOT NULL UNIQUE, official_url TEXT, opportunity_type TEXT NOT NULL,
 created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS program_aliases(
 alias_key TEXT PRIMARY KEY, program_id TEXT NOT NULL REFERENCES funding_programs(id),
 alias TEXT NOT NULL, reason TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS funding_cycles(
 id TEXT PRIMARY KEY, program_id TEXT NOT NULL REFERENCES funding_programs(id),
 cycle_key TEXT NOT NULL, label TEXT NOT NULL, UNIQUE(program_id,cycle_key)
);
CREATE TABLE IF NOT EXISTS funding_intelligence(
 opportunity_id TEXT PRIMARY KEY REFERENCES opportunities(id),
 program_id TEXT NOT NULL REFERENCES funding_programs(id), cycle_id TEXT NOT NULL UNIQUE REFERENCES funding_cycles(id),
 data_json TEXT NOT NULL, analysis_json TEXT NOT NULL, recommendation TEXT NOT NULL,
 verification_state TEXT NOT NULL, score_min REAL NOT NULL, score_max REAL NOT NULL,
 fit_score REAL, last_verified TEXT, discovered_at TEXT NOT NULL, last_checked TEXT NOT NULL,
 next_check TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS funding_versions(
 id TEXT PRIMARY KEY, opportunity_id TEXT NOT NULL REFERENCES opportunities(id), run_id TEXT,
 data_json TEXT NOT NULL, analysis_json TEXT NOT NULL, captured_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS funding_sources(
 id TEXT PRIMARY KEY, url TEXT NOT NULL, role TEXT NOT NULL, checked_at TEXT NOT NULL,
 content_sha256 TEXT NOT NULL, excerpt TEXT NOT NULL, fetch_status TEXT NOT NULL,
 UNIQUE(url,content_sha256,role)
);
CREATE TABLE IF NOT EXISTS funding_source_links(
 opportunity_id TEXT NOT NULL REFERENCES opportunities(id), source_id TEXT NOT NULL REFERENCES funding_sources(id),
 PRIMARY KEY(opportunity_id,source_id)
);
CREATE TABLE IF NOT EXISTS company_fact_values(
 claim_version_id TEXT NOT NULL REFERENCES claim_versions(id), fact_key TEXT NOT NULL,
 value_json TEXT NOT NULL, PRIMARY KEY(claim_version_id,fact_key)
);
CREATE TABLE IF NOT EXISTS funding_runs(
 id TEXT PRIMARY KEY, request_key TEXT NOT NULL UNIQUE, input_hash TEXT NOT NULL,
 started_at TEXT NOT NULL, completed_at TEXT, state TEXT NOT NULL,
 report_json TEXT NOT NULL, usage_json TEXT NOT NULL, lease_until TEXT
);
CREATE TABLE IF NOT EXISTS funding_candidates(
 id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES funding_runs(id),
 title TEXT NOT NULL, url TEXT NOT NULL, family TEXT NOT NULL,
 state TEXT NOT NULL, detail_json TEXT NOT NULL, UNIQUE(run_id,url)
);
CREATE TABLE IF NOT EXISTS funding_decisions(
 id TEXT PRIMARY KEY, opportunity_id TEXT NOT NULL REFERENCES opportunities(id),
 recommendation TEXT NOT NULL, score_json TEXT NOT NULL, decision TEXT NOT NULL,
 reason TEXT NOT NULL, created_at TEXT NOT NULL, actor TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS funding_outcomes(
 id TEXT PRIMARY KEY, opportunity_id TEXT NOT NULL REFERENCES opportunities(id),
 application_id TEXT REFERENCES applications(id), submission_id TEXT REFERENCES submissions(id),
 outcome TEXT NOT NULL, source_version_id TEXT REFERENCES source_versions(id),
 evidence_url TEXT, evidence_note TEXT NOT NULL, occurred_at TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS funding_notifications(
 id TEXT PRIMARY KEY, opportunity_id TEXT NOT NULL REFERENCES opportunities(id), kind TEXT NOT NULL,
 payload_json TEXT NOT NULL, created_at TEXT NOT NULL, read_at TEXT,
 dedup_key TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS material_registry(
 id TEXT PRIMARY KEY, source_version_id TEXT NOT NULL REFERENCES source_versions(id),
 kind TEXT NOT NULL, label TEXT NOT NULL, status TEXT NOT NULL,
 claim_versions_json TEXT NOT NULL, checked_at TEXT,
 UNIQUE(source_version_id,kind)
);
CREATE TABLE IF NOT EXISTS program_history(
 id TEXT PRIMARY KEY, program_id TEXT NOT NULL REFERENCES funding_programs(id),
 cycle_id TEXT REFERENCES funding_cycles(id), source_version_id TEXT REFERENCES source_versions(id),
 original_path TEXT, locator TEXT NOT NULL, kind TEXT NOT NULL, note TEXT NOT NULL,
 UNIQUE(program_id,original_path,locator,kind)
);
CREATE TABLE IF NOT EXISTS hunter_settings(key TEXT PRIMARY KEY,value_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS scoring_versions(id TEXT PRIMARY KEY,body_json TEXT NOT NULL,created_at TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS hunter_requests(
 id TEXT PRIMARY KEY, request_key TEXT NOT NULL UNIQUE, reason TEXT NOT NULL,
 state TEXT NOT NULL, created_at TEXT NOT NULL, run_id TEXT REFERENCES funding_runs(id)
);
CREATE INDEX IF NOT EXISTS hunter_due ON funding_intelligence(next_check);
CREATE TRIGGER IF NOT EXISTS funding_version_immutable BEFORE UPDATE ON funding_versions BEGIN SELECT RAISE(ABORT,'Research versions are immutable'); END;
CREATE TRIGGER IF NOT EXISTS funding_version_retain BEFORE DELETE ON funding_versions BEGIN SELECT RAISE(ABORT,'Research versions cannot be deleted'); END;
CREATE TRIGGER IF NOT EXISTS funding_source_immutable BEFORE UPDATE ON funding_sources BEGIN SELECT RAISE(ABORT,'Research sources are immutable'); END;
CREATE TRIGGER IF NOT EXISTS funding_source_retain BEFORE DELETE ON funding_sources BEGIN SELECT RAISE(ABORT,'Research sources cannot be deleted'); END;
CREATE TRIGGER IF NOT EXISTS fact_value_immutable BEFORE UPDATE ON company_fact_values BEGIN SELECT RAISE(ABORT,'Structured claim values are immutable'); END;
CREATE TRIGGER IF NOT EXISTS fact_value_retain BEFORE DELETE ON company_fact_values BEGIN SELECT RAISE(ABORT,'Structured claim values are immutable'); END;
CREATE TRIGGER IF NOT EXISTS fact_value_before_review BEFORE INSERT ON company_fact_values
 WHEN (SELECT status FROM claim_reviews WHERE version_id=NEW.claim_version_id)!='proposed'
 OR EXISTS(SELECT 1 FROM approvals WHERE action='promote_claim' AND json_extract(payload_json,'$.version_id')=NEW.claim_version_id)
 BEGIN SELECT RAISE(ABORT,'Bind structured values before preparing approval'); END;
