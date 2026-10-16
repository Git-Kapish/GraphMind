import React from 'react';
import { Database, Network } from 'lucide-react';
import GraphCanvas from './GraphCanvas';

export default function CompareView({
  baselineData,
  hybridData,
  loading,
  onSelectCitation,
}) {
  if (loading) {
    return (
      <div className="compare-loading-card glass-panel fade-in">
        <div className="orbit-spinner"></div>
        <h3>Running Dual Execution: System A (Vector Baseline) vs System C (Hybrid KG-RAG)...</h3>
        <p className="loading-subtext">Evaluating dense cosine similarity in parallel with Cypher graph path traversal.</p>
      </div>
    );
  }

  if (!baselineData && !hybridData) {
    return null;
  }

  return (
    <div className="compare-container fade-in">
      <div className="compare-banner glass-panel">
        <div className="compare-banner-content">
          <h4>A/B Head-to-Head Comparison</h4>
          <p>
            Comparing <strong>System A (Dense Vector Baseline)</strong> against <strong>System C (Hybrid Auto-Routed KG-RAG)</strong> on the exact same SEC 10-K query.
          </p>
        </div>
      </div>

      <div className="compare-grid">
        {/* System A: Plain Vector Baseline */}
        <div className="compare-column baseline-column glass-panel">
          <div className="column-header">
            <div className="column-title-strip">
              <Database size={18} className="text-cyan" />
              <h3>System A: Vector Baseline</h3>
            </div>
            <span className="badge badge-vector">Dense pgvector (k=5)</span>
          </div>

          <div className="column-telemetry">
            <div className="col-stat">
              <span className="stat-label">Latency:</span>
              <span className="stat-val font-mono">{baselineData?.latency?.total_ms || 0} ms</span>
            </div>
            <div className="col-stat">
              <span className="stat-label">Route:</span>
              <span className="stat-val font-mono">vector_only</span>
            </div>
            <div className="col-stat">
              <span className="stat-label">Passages:</span>
              <span className="stat-val font-mono">{baselineData?.passages?.length || 0} chunks</span>
            </div>
          </div>

          <div className="column-answer-box">
            <h4>Generated Answer:</h4>
            <p className="column-answer-text">
              {baselineData?.answer || "No response received from baseline."}
            </p>
          </div>

          <div className="column-passages-box">
            <h4>Retrieved Passages:</h4>
            {baselineData?.passages && baselineData.passages.length > 0 ? (
              <div className="col-passage-list">
                {baselineData.passages.map((p, idx) => (
                  <div key={idx} className="col-passage-item">
                    <span className="badge badge-vector">[P{idx + 1}]</span>
                    <span className="company-tag">{p.company}</span>
                    <p className="passage-txt">{p.text.slice(0, 140)}...</p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-muted">No passages returned.</p>
            )}
          </div>
        </div>

        {/* System C: Hybrid Auto-Routed KG-RAG */}
        <div className="compare-column hybrid-column glass-panel glass-card-glow">
          <div className="column-header">
            <div className="column-title-strip">
              <Network size={18} className="text-emerald" />
              <h3>System C: Hybrid KG-RAG</h3>
            </div>
            <span className="badge badge-hybrid">Auto-Routed (Primary)</span>
          </div>

          <div className="column-telemetry">
            <div className="col-stat">
              <span className="stat-label">Latency:</span>
              <span className="stat-val font-mono">{hybridData?.latency?.total_ms || 0} ms</span>
            </div>
            <div className="col-stat">
              <span className="stat-label">Route Chosen:</span>
              <span className="stat-val font-mono text-emerald">
                {hybridData?.route?.chosen?.toUpperCase() || 'HYBRID'}
              </span>
            </div>
            <div className="col-stat">
              <span className="stat-label">Graph Paths:</span>
              <span className="stat-val font-mono text-emerald">
                {hybridData?.graph_paths?.length || 0} paths
              </span>
            </div>
          </div>

          <div className="column-answer-box">
            <h4>Grounded Answer (With Citations):</h4>
            <p className="column-answer-text">
              {hybridData?.answer || "No response received from hybrid system."}
            </p>
          </div>

          {hybridData?.graph_paths && hybridData.graph_paths.length > 0 ? (
            <div className="column-graph-preview">
              <GraphCanvas graphPaths={hybridData.graph_paths} onSelectEvidence={onSelectCitation} />
            </div>
          ) : (
            <div className="column-passages-box">
              <h4>Retrieved Passages:</h4>
              <div className="col-passage-list">
                {(hybridData?.passages || []).map((p, idx) => (
                  <div key={idx} className="col-passage-item">
                    <span className="badge badge-hybrid">[P{idx + 1}]</span>
                    <span className="company-tag">{p.company}</span>
                    <p className="passage-txt">{p.text.slice(0, 140)}...</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
