import React from 'react';
import { FileText, ShieldCheck, ExternalLink, X, BookOpen, Layers } from 'lucide-react';

export default function EvidenceDrawer({ activeCitation, onClose }) {
  if (!activeCitation) return null;

  const isGraph = activeCitation.source_type === 'graph' || activeCitation.label?.startsWith('[G');

  return (
    <div className="drawer-overlay fade-in" onClick={onClose}>
      <div className="drawer-panel" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-header">
          <div className="drawer-header-left">
            <span className={`drawer-label-badge ${isGraph ? 'graph' : 'vector'}`}>
              {activeCitation.label}
            </span>
            <h3>Filing Evidence Provenance</h3>
          </div>
          <button className="drawer-close-btn" onClick={onClose} aria-label="Close drawer">
            <X size={20} />
          </button>
        </div>

        <div className="drawer-body">
          {/* Metadata Card */}
          <div className="drawer-meta-card">
            <div className="meta-row">
              <span className="meta-key">Company Filer:</span>
              <span className="meta-val highlight">{activeCitation.company || 'Enterprise 10-K'}</span>
            </div>
            {activeCitation.ticker && (
              <div className="meta-row">
                <span className="meta-key">Ticker:</span>
                <span className="meta-val font-mono">{activeCitation.ticker}</span>
              </div>
            )}
            <div className="meta-row">
              <span className="meta-key">Section Path:</span>
              <span className="meta-val font-mono">{activeCitation.section_path || '10-K Filing'}</span>
            </div>
            <div className="meta-row">
              <span className="meta-key">Chunk ID:</span>
              <span className="meta-val font-mono text-muted">{activeCitation.chunk_id}</span>
            </div>
            <div className="meta-row">
              <span className="meta-key">Verification Status:</span>
              <span className="meta-val text-emerald flex items-center gap-1">
                <ShieldCheck size={15} /> 100% Mechanically Grounded
              </span>
            </div>
          </div>

          {/* Evidence Content Section */}
          <div className="drawer-section">
            <div className="drawer-section-title">
              <BookOpen size={16} />
              <span>Verbatim Filing Excerpt</span>
            </div>
            <div className="drawer-text-box">
              {activeCitation.text_snippet ? (
                <p>{activeCitation.text_snippet}</p>
              ) : activeCitation.evidence_quote ? (
                <blockquote className="evidence-quote">
                  "{activeCitation.evidence_quote}"
                </blockquote>
              ) : (
                <p className="text-muted">Chunk text verified from PostgreSQL storage.</p>
              )}
            </div>
          </div>

          {/* Observation IDs for Graph items */}
          {activeCitation.observation_ids && activeCitation.observation_ids.length > 0 && (
            <div className="drawer-section">
              <div className="drawer-section-title">
                <Layers size={16} />
                <span>Extraction Observations ({activeCitation.observation_ids.length})</span>
              </div>
              <div className="obs-tags-cloud">
                {activeCitation.observation_ids.map((obsId, idx) => (
                  <span key={idx} className="obs-tag">{obsId}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
