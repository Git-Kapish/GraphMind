# Architectural & Gate Decisions Log (docs/DECISIONS.md)

| Date | Milestone | Decision | Context & Rationale | Status |
|---|---|---|---|---|
| 2026-10-15 | M0 | Adopt Python 3.12 with uv and Pydantic v2 | Python 3.12 is fully compatible with pgvector, psycopg, neo4j, and edgartools; managed by uv. | Approved |
| 2026-10-15 | M0 | Ollama local runtime with nomic-embed-text & llama3.2 | $0 model spend constraint; local-first; nomic-embed-text matches 768-d pgvector configuration. | Approved |
| 2026-10-15 | M0 | PostgreSQL as authoritative source of truth | Neo4j is a rebuildable projection from extraction_observations. | Approved |
