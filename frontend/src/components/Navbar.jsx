import React from 'react';
import { Database, Network, Cpu, BarChart3 } from 'lucide-react';

export default function Navbar({ onOpenBenchmark }) {
  return (
    <header className="navbar-container">
      <div className="navbar-left">
        <div className="navbar-brand-icon">
          <Network className="icon-glow" size={24} />
        </div>
        <div>
          <div className="navbar-title-row">
            <h1 className="navbar-title">GraphMind</h1>
            <span className="navbar-badge">SEC 10-K RAG</span>
          </div>
          <p className="navbar-subtitle">Hybrid Knowledge Graph & Vector RAG with Citation Validation</p>
        </div>
      </div>

      <div className="navbar-right">
        {/* System Health Indicators */}
        <div className="health-strip">
          <div className="health-pill" title="PostgreSQL 16 + pgvector (789 chunks)">
            <Database size={14} className="health-icon pg-icon" />
            <span>Postgres 2048d</span>
            <span className="health-indicator active"></span>
          </div>

          <div className="health-pill" title="Neo4j 5.26 (331 nodes, 481 relationships)">
            <Network size={14} className="health-icon neo-icon" />
            <span>Neo4j Graph</span>
            <span className="health-indicator active"></span>
          </div>

          <div className="health-pill" title="OpenRouter Free Tier ($0 spend)">
            <Cpu size={14} className="health-icon llm-icon" />
            <span>Nemotron 3.5 ($0)</span>
            <span className="health-indicator active"></span>
          </div>
        </div>

        {/* Benchmark Button */}
        <button className="benchmark-trigger-btn" onClick={onOpenBenchmark}>
          <BarChart3 size={16} />
          <span>M10 Benchmark</span>
        </button>
      </div>
    </header>
  );
}
