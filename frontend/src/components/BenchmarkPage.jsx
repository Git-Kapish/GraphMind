import React from 'react';
import { X, BarChart3 } from 'lucide-react';

export default function BenchmarkPage() {
  return (
    <div className="benchmark-page">
      <nav className="benchmark-breadcrumb">
        <a href="/" className="breadcrumb-link">Home</a>
        <span className="breadcrumb-separator">/</span>
        <span className="breadcrumb-active">Benchmark Results</span>
      </nav>

      <header className="page-header">
        <h1>Milestone M10: 5-Way Ablation Benchmark & Statistical Policy</h1>
        <p className="page-subtitle">Comprehensive benchmark analysis across 5 system configurations</p>
      </header>

      <main className="benchmark-content">
        {/* Summary Cards */}
        <div className="benchmark-stat-cards">
          <div className="stat-card">
            <span className="stat-title">Target Model</span>
            <span className="stat-value">Qwen 2.5 3B</span>
            <span className="stat-sub">$0 spend local CPU</span>
          </div>
          <div className="stat-card">
            <span className="stat-title">Knowledge Graph</span>
            <span className="stat-value text-emerald">331 Nodes</span>
            <span className="stat-sub">481 Neo4j edges</span>
          </div>
          <div className="stat-card">
            <span className="stat-title">Dense Vector Store</span>
            <span className="stat-value text-cyan">789 Chunks</span>
            <span className="stat-sub">768-d pgvector nomic</span>
          </div>
          <div className="stat-card">
            <span className="stat-title">Citation Resolution</span>
            <span className="stat-value text-emerald">100.0%</span>
            <span className="stat-sub">Strict mechanical proof</span>
          </div>
        </div>

        {/* 5-Way System Comparison Table */}
        <section className="benchmark-section">
          <h2>1. 5-Way System Comparison & Wilson 95% Confidence Intervals</h2>
          <div className="table-responsive">
            <table className="benchmark-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>System Architecture</th>
                  <th>Accuracy</th>
                  <th>Wilson 95% CI</th>
                  <th>Citation Resolution</th>
                  <th>Latency (p50 / p95)</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td><strong>A</strong></td>
                  <td>System A (Vector Baseline)</td>
                  <td><strong>87.5%</strong> (7/8)</td>
                  <td><code>[52.9%, 97.8%]</code></td>
                  <td>100.0%</td>
                  <td>41,935 ms / 55,793 ms</td>
                </tr>
                <tr>
                  <td><strong>B</strong></td>
                  <td>System B (Graph-Only)</td>
                  <td><strong>50.0%</strong> (4/8)</td>
                  <td><code>[21.5%, 78.5%]</code></td>
                  <td>100.0%</td>
                  <td>5,103 ms / 11,258 ms</td>
                </tr>
                <tr className="highlight-row">
                  <td><strong>C</strong></td>
                  <td><strong>System C (Hybrid Auto-Routed)</strong></td>
                  <td><strong className="text-emerald">87.5%</strong> (7/8)</td>
                  <td><code>[52.9%, 97.8%]</code></td>
                  <td><strong className="text-emerald">100.0%</strong></td>
                  <td>28,373 ms / 45,482 ms</td>
                </tr>
                <tr>
                  <td><strong>D</strong></td>
                  <td>System D (Hybrid-Always)</td>
                  <td><strong>87.5%</strong> (7/8)</td>
                  <td><code>[52.9%, 97.8%]</code></td>
                  <td>100.0%</td>
                  <td>3,222 ms / 7,147 ms</td>
                </tr>
                <tr>
                  <td><strong>E</strong></td>
                  <td>System E (Oracle Diagnostic)</td>
                  <td><strong>87.5%</strong> (7/8)</td>
                  <td><code>[52.9%, 97.8%]</code></td>
                  <td>100.0%</td>
                  <td>2,445 ms / 6,520 ms</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        {/* Category Breakdown Table */}
        <section className="benchmark-section">
          <h2>2. Category Breakdown & PRD §2.2 Statistical Status</h2>
          <div className="table-responsive">
            <table className="benchmark-table">
              <thead>
                <tr>
                  <th>Category</th>
                  <th>Sample N</th>
                  <th>Statistical Status</th>
                  <th>Vector (A)</th>
                  <th>Hybrid (C)</th>
                  <th>Delta (C - A)</th>
                  <th>McNemar p-value</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td><code>single_hop</code></td>
                  <td>2</td>
                  <td><span className="badge-exploratory">[Exploratory: N &lt; 15]</span></td>
                  <td>100.0%</td>
                  <td><strong>100.0%</strong></td>
                  <td>+0.0%</td>
                  <td>1.0000</td>
                </tr>
                <tr>
                  <td><code>two_hop</code></td>
                  <td>2</td>
                  <td><span className="badge-exploratory">[Exploratory: N &lt; 15]</span></td>
                  <td>100.0%</td>
                  <td><strong>100.0%</strong></td>
                  <td>+0.0%</td>
                  <td>1.0000</td>
                </tr>
                <tr>
                  <td><code>multi_hop</code></td>
                  <td>2</td>
                  <td><span className="badge-exploratory">[Exploratory: N &lt; 15]</span></td>
                  <td>50.0%</td>
                  <td><strong>50.0%</strong></td>
                  <td>+0.0%</td>
                  <td>1.0000</td>
                </tr>
                <tr>
                  <td><code>out_of_scope</code></td>
                  <td>2</td>
                  <td><span className="badge-exploratory">[Exploratory: N &lt; 15]</span></td>
                  <td>100.0%</td>
                  <td><strong>100.0%</strong></td>
                  <td>+0.0%</td>
                  <td>1.0000</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        {/* Failure Taxonomy */}
        <section className="benchmark-section">
          <h2>3. Failure Taxonomy & Root Cause Analysis (PRD FR-5.2)</h2>
          <div className="table-responsive">
            <table className="benchmark-table">
              <thead>
                <tr>
                  <th>System</th>
                  <th>Retrieval Miss</th>
                  <th>Generation Error</th>
                  <th>Refusal Error</th>
                  <th>Router Error</th>
                  <th>Total Errors</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td><strong>System A (Vector Baseline)</strong></td>
                  <td>0</td>
                  <td>1</td>
                  <td>0</td>
                  <td>0</td>
                  <td>1</td>
                </tr>
                <tr>
                  <td><strong>System B (Graph-Only)</strong></td>
                  <td>4</td>
                  <td>0</td>
                  <td>0</td>
                  <td>0</td>
                  <td>4 (refusal on unmodeled paths)</td>
                </tr>
                <tr className="highlight-row">
                  <td><strong>System C (Hybrid Auto-Routed)</strong></td>
                  <td>0</td>
                  <td>1</td>
                  <td>0</td>
                  <td>0</td>
                  <td>1 (0 router errors)</td>
                </tr>
                <tr>
                  <td><strong>System E (Oracle Diagnostic)</strong></td>
                  <td>1</td>
                  <td>0</td>
                  <td>0</td>
                  <td>0</td>
                  <td>1</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </main>
    </div>
  );
}