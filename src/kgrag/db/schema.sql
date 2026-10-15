-- Schema DDL for Knowledge Graph RAG (PRD §9.1)

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
    doc_id VARCHAR(64) PRIMARY KEY,
    company VARCHAR(255) NOT NULL,
    ticker VARCHAR(16) NOT NULL,
    cik VARCHAR(16) NOT NULL,
    form_type VARCHAR(16) NOT NULL,
    fiscal_year INT NOT NULL,
    filing_date DATE NOT NULL,
    accession VARCHAR(64) NOT NULL,
    source_url TEXT NOT NULL,
    sha256 VARCHAR(64) NOT NULL,
    ingested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chunks (
    chunk_id VARCHAR(128) PRIMARY KEY,
    doc_id VARCHAR(64) REFERENCES documents(doc_id) ON DELETE CASCADE,
    section_path VARCHAR(255) NOT NULL,
    item VARCHAR(32) NOT NULL,
    text TEXT NOT NULL,
    token_count INT NOT NULL,
    char_start INT NOT NULL,
    char_end INT NOT NULL,
    entity_ids TEXT[] DEFAULT '{}',
    embedding vector(768),
    embedding_model VARCHAR(64),
    chunker_version VARCHAR(32)
);
CREATE INDEX IF NOT EXISTS idx_chunks_doc_id ON chunks(doc_id);
CREATE INDEX IF NOT EXISTS idx_chunks_item ON chunks(item);

CREATE TABLE IF NOT EXISTS entities (
    entity_id VARCHAR(64) PRIMARY KEY,
    type VARCHAR(32) NOT NULL,
    canonical_name VARCHAR(255) NOT NULL,
    aliases TEXT[] DEFAULT '{}',
    name_embedding vector(768),
    embedding_model VARCHAR(64)
);
CREATE INDEX IF NOT EXISTS idx_entities_canonical_name ON entities(canonical_name);

CREATE TABLE IF NOT EXISTS extraction_cache (
    chunk_sha256 VARCHAR(64),
    model VARCHAR(64),
    prompt_version VARCHAR(32),
    ontology_version VARCHAR(32),
    schema_version VARCHAR(32),
    status VARCHAR(32) NOT NULL,
    result_json JSONB,
    tokens_in INT,
    tokens_out INT,
    latency_ms INT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(chunk_sha256, model, prompt_version, ontology_version, schema_version)
);

CREATE TABLE IF NOT EXISTS extraction_observations (
    observation_id VARCHAR(64) PRIMARY KEY,
    chunk_id VARCHAR(128) REFERENCES chunks(chunk_id) ON DELETE CASCADE,
    extraction_method VARCHAR(32) NOT NULL, -- 'llm' | 'parser'
    head_surface VARCHAR(255) NOT NULL,
    head_type VARCHAR(32) NOT NULL,
    relation_type VARCHAR(64) NOT NULL,
    tail_surface VARCHAR(255) NOT NULL,
    tail_type VARCHAR(32) NOT NULL,
    head_entity_id VARCHAR(64) REFERENCES entities(entity_id),
    tail_entity_id VARCHAR(64) REFERENCES entities(entity_id),
    resolution_status VARCHAR(32) DEFAULT 'pending', -- 'pending' | 'resolved' | 'needs_review' | 'unresolvable'
    evidence_quote TEXT NOT NULL,
    evidence_verified BOOLEAN DEFAULT FALSE,
    model_confidence FLOAT,
    role VARCHAR(128),
    year INT,
    validation_result JSONB,
    model VARCHAR(64),
    prompt_version VARCHAR(32),
    ontology_version VARCHAR(32),
    schema_version VARCHAR(32),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_obs_chunk_id ON extraction_observations(chunk_id);
CREATE INDEX IF NOT EXISTS idx_obs_endpoints ON extraction_observations(head_entity_id, tail_entity_id);
CREATE INDEX IF NOT EXISTS idx_obs_status ON extraction_observations(resolution_status, evidence_verified);

CREATE TABLE IF NOT EXISTS entity_merge_history (
    id SERIAL PRIMARY KEY,
    source_entity_id VARCHAR(64) NOT NULL,
    canonical_entity_id VARCHAR(64) NOT NULL,
    decision VARCHAR(32) NOT NULL,
    method VARCHAR(64) NOT NULL,
    score FLOAT,
    reviewer_note TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS routing_log (
    id SERIAL PRIMARY KEY,
    ts TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    question TEXT NOT NULL,
    route VARCHAR(32) NOT NULL,
    confidence FLOAT,
    fallback_used BOOLEAN DEFAULT FALSE,
    outcome VARCHAR(64),
    latency_ms INT,
    request_id VARCHAR(64) NOT NULL
);

CREATE TABLE IF NOT EXISTS ingestion_checkpoints (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(64) NOT NULL,
    ticker VARCHAR(16) NOT NULL,
    stage VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL,
    records_processed INT DEFAULT 0,
    elapsed_seconds FLOAT DEFAULT 0.0,
    metadata JSONB DEFAULT '{}',
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_ingestion_checkpoint_ticker_stage ON ingestion_checkpoints(ticker, stage);
CREATE INDEX IF NOT EXISTS idx_ingestion_checkpoint_run_id ON ingestion_checkpoints(run_id);

