-- ADR-027: EAKG non-graph artifacts (registry / interface / OpenAPI / ApiIndex ops)
-- Plus embeddings, proposals, decisions, engineering, GraphRAG, SOP cache.

CREATE TABLE IF NOT EXISTS eakg_registry (
    id SMALLINT PRIMARY KEY CHECK (id = 1),
    payload JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS eakg_interface (
    repository_id TEXT PRIMARY KEY,
    commit_sha TEXT NOT NULL DEFAULT '',
    content_hash TEXT NOT NULL DEFAULT '',
    payload JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS eakg_openapi (
    repository_id TEXT NOT NULL,
    environment TEXT NOT NULL,
    spec_hash TEXT NOT NULL DEFAULT '',
    source_url TEXT NOT NULL DEFAULT '',
    pointer JSONB NOT NULL DEFAULT '{}'::jsonb,
    payload JSONB,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (repository_id, environment)
);

CREATE TABLE IF NOT EXISTS eakg_manifest (
    repository_id TEXT PRIMARY KEY,
    payload JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS eakg_operations (
    environment TEXT PRIMARY KEY,
    payload JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS eakg_capability_embeddings (
    id SMALLINT PRIMARY KEY CHECK (id = 1),
    payload JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS eakg_proposals (
    repository_id TEXT NOT NULL,
    seq BIGSERIAL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (repository_id, seq)
);

CREATE TABLE IF NOT EXISTS eakg_decisions (
    seq BIGSERIAL PRIMARY KEY,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS eakg_engineering (
    repository_id TEXT NOT NULL,
    artifact_name TEXT NOT NULL,
    payload JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (repository_id, artifact_name)
);

CREATE TABLE IF NOT EXISTS eakg_graphrag (
    artifact_key TEXT PRIMARY KEY,
    payload JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS eakg_kv (
    key TEXT PRIMARY KEY,
    payload JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS sop_page_cache (
    path TEXT PRIMARY KEY,
    body TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS eakg_pipeline_runs (
    run_id TEXT PRIMARY KEY,
    pipeline_id TEXT NOT NULL,
    payload JSONB NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS eakg_pipeline_runs_by_pipeline
    ON eakg_pipeline_runs (pipeline_id, started_at DESC);

CREATE TABLE IF NOT EXISTS eakg_asset_state (
    asset_key TEXT PRIMARY KEY,
    payload JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
