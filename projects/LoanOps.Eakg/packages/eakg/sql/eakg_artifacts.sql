-- ADR-027: EAKG non-graph artifacts (registry / interface / OpenAPI / ApiIndex ops)

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
