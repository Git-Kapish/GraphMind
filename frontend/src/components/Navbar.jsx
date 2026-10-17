import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Database, Network, Cpu, BarChart3 } from 'lucide-react';

export default function Navbar({ health }) {
  const location = useLocation();

  const isActive = (path) => location.pathname === path || (location.pathname.startsWith(path) && location.pathname !== '/');

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

        {/* Navigation Links */}
        <div className="nav-links">
          <Link to="/" className={`nav-link ${isActive('/') ? 'active' : ''}`}>Search</Link>
          <Link to="/benchmark" className={`nav-link ${isActive('/benchmark') ? 'active' : ''}`}>Benchmark</Link>
          <Link to="/project" className={`nav-link ${isActive('/project') ? 'active' : ''}`}>Project Info</Link>
        </div>
      </div>
    </header>
  );
}
