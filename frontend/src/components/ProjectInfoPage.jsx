import React from 'react';

export default function ProjectInfoPage() {
  return (
    <div className="project-info-page">
      <nav className="project-breadcrumb">
        <a href="/" className="breadcrumb-link">Home</a>
        <span className="breadcrumb-separator">/</span>
        <span className="breadcrumb-active">Project Information</span>
      </nav>

      <header className="page-header">
        <h1>GraphMind</h1>
        <p className="page-subtitle">Hybrid Knowledge Graph & Vector RAG with Citation Validation</p>
      </header>

      <main className="project-content">
        <section className="project-overview">
          <h2>Overview</h2>
          <p>GraphMind is a hybrid Knowledge Graph & Vector RAG system that leverages SEC 10-K filings from 10 enterprise companies to provide accurate, citation-backed answers to relational and multi-hop financial questions.</p>
          <p>The system combines the strengths of dense vector retrieval with structured graph-based knowledge, enabling users to traverse enterprise data through both semantic similarity and relational queries.</p>
        </section>

        <section className="problem-statement">
          <h2>Problem It Solves</h2>
          <p>Traditional RAG systems often struggle with multi-hop reasoning and providing verifiable sources for their answers. GraphMind addresses this by:</p>
          <ul>
            <li><strong>Knowledge Graph:</strong> Modeling entity relationships from 10-K filings to enable multi-hop traversal and context-aware retrieval</li>
            <li><strong>Vector Search:</strong> Using dense embeddings (nomic-768d) for semantic similarity matching across chunked filing content</li>
            <li><strong>Citation Validation:</strong> Mechanically grounding every answer to source passages with 100% resolution rate</li>
            <li><strong>Hybrid Routing:</strong> Dynamically selecting the optimal retrieval strategy (vector, graph, or hybrid) based on query characteristics</li>
          </ul>
        </section>

        <section className="dataset-used">
          <h2>Dataset Used</h2>
          <p>The system processes SEC 10-K financial filings from 10 enterprise companies, providing comprehensive coverage of:</p>
          <ul>
            <li>Corporate structure and subsidiaries (331 graph nodes)</li>
            <li>Financial metrics and performance data</li>
            <li>Risk factors and legal proceedings</li>
            <li>Executive compensation and governance</li>
            <li>Market operations and subsidiaries</li>
          </ul>
          <p>The knowledge graph contains 331 nodes and 481 Neo4j edges, representing companies, subsidiaries, people, concepts, and their relationships extracted from the filings.</p>
        </section>

        <section className="key-metrics">
          <h2>Key Metrics</h2>
          <div className="metrics-grid">
            <div className="metric-card">
              <span className="metric-value">331</span>
              <span className="metric-label">Neo4j Nodes</span>
            </div>
            <div className="metric-card">
              <span className="metric-value">481</span>
              <span className="metric-label">Neo4j Edges</span>
            </div>
            <div className="metric-card">
              <span className="metric-value">789</span>
              <span className="metric-label">pgvector Chunks</span>
            </div>
            <div className="metric-card">
              <span className="metric-value">Qwen 2.5 3B</span>
              <span className="metric-label">Target Model</span>
            </div>
            <div className="metric-card">
              <span className="metric-value">100.0%</span>
              <span className="metric-label">Citation Resolution</span>
            </div>
            <div className="metric-card">
              <span className="metric-value">10</span>
              <span className="metric-label">Enterprise Companies</span>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}