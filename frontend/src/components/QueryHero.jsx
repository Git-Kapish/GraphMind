import React from 'react';
import { Search, Sparkles, SlidersHorizontal, ArrowRight, CornerDownLeft, SplitSquareVertical } from 'lucide-react';

const EXAMPLE_CATEGORIES = [
  {
    name: 'Multi-Hop (Graph Wins)',
    tag: 'multi_hop',
    questions: [
      "Which subsidiaries of AMD operate in Singapore according to Exhibit 21?",
      "Which enterprise technology companies operate major subsidiaries in Ireland?",
      "In which Scandinavian countries does AMD maintain operating subsidiaries through Silo AI?",
    ],
  },
  {
    name: 'Two-Hop Relational',
    tag: 'two_hop',
    questions: [
      "In what country does AMD's subsidiary Silo AI Oy operate?",
      "In what jurisdiction does the Broadcom subsidiary VMware Management operate?",
      "In what Asian nation is Qualcomm's manufacturing subsidiary RF360 located?",
    ],
  },
  {
    name: 'Single-Hop Relational',
    tag: 'single_hop',
    questions: [
      "Who were the founders of Intel Corporation?",
      "Where is Microsoft's corporate headquarters located?",
      "What subsidiary does NVIDIA operate in Singapore according to its disclosures?",
    ],
  },
  {
    name: 'Adversarial Refusals',
    tag: 'out_of_scope',
    questions: [
      "Who is the Chief Technology Officer of Tesla Inc.?",
      "What was the weather in Redmond Washington during Microsoft's founding?",
    ],
  },
];

export default function QueryHero({
  query,
  setQuery,
  mode,
  setMode,
  onSearch,
  loading,
}) {
  const handleSubmit = (e) => {
    e.preventDefault();
    if (query.trim() && !loading) {
      onSearch(query);
    }
  };

  return (
    <div className="query-hero-card glass-panel glass-card-glow">
      {/* Mode Selector Tabs */}
      <div className="mode-tabs-container">
        <span className="mode-label">Retrieval Mode:</span>
        <div className="mode-pills">
          <button
            type="button"
            className={`mode-pill ${mode === 'auto' ? 'active auto' : ''}`}
            onClick={() => setMode('auto')}
          >
            <Sparkles size={14} />
            <span>Auto-Routed (Hybrid)</span>
          </button>

          <button
            type="button"
            className={`mode-pill ${mode === 'compare' ? 'active compare' : ''}`}
            onClick={() => setMode('compare')}
          >
            <SplitSquareVertical size={14} />
            <span>Compare A/B (Vector vs Hybrid)</span>
          </button>

          <button
            type="button"
            className={`mode-pill ${mode === 'vector' ? 'active vector' : ''}`}
            onClick={() => setMode('vector')}
          >
            <span>Vector Baseline (A)</span>
          </button>

          <button
            type="button"
            className={`mode-pill ${mode === 'graph' ? 'active graph' : ''}`}
            onClick={() => setMode('graph')}
          >
            <span>Graph-Only (B)</span>
          </button>

          <button
            type="button"
            className={`mode-pill ${mode === 'hybrid' ? 'active forced' : ''}`}
            onClick={() => setMode('hybrid')}
          >
            <span>Forced Hybrid (D)</span>
          </button>
        </div>
      </div>

      {/* Main Search Bar Form */}
      <form onSubmit={handleSubmit} className="search-form">
        <div className="search-input-wrapper">
          <Search className="search-icon" size={20} />
          <input
            type="text"
            className="search-input"
            placeholder="Ask a relational or multi-hop financial question across 10 enterprise SEC 10-K filings..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={loading}
          />
          {query && !loading && (
            <button
              type="button"
              className="clear-btn"
              onClick={() => setQuery('')}
            >
              ×
            </button>
          )}
          <button
            type="submit"
            className={`search-submit-btn ${loading ? 'loading' : ''}`}
            disabled={!query.trim() || loading}
          >
            {loading ? (
              <span className="spinner"></span>
            ) : (
              <>
                <span>Execute</span>
                <CornerDownLeft size={16} />
              </>
            )}
          </button>
        </div>
      </form>

      {/* Pre-Loaded Example Questions by Category */}
      <div className="examples-section">
        <div className="examples-header">
          <SlidersHorizontal size={13} />
          <span>Curated Benchmark Questions:</span>
        </div>
        <div className="examples-groups">
          {EXAMPLE_CATEGORIES.map((cat) => (
            <div key={cat.tag} className="example-group">
              <span className={`example-cat-tag ${cat.tag}`}>{cat.name}</span>
              <div className="example-buttons">
                {cat.questions.map((q, idx) => (
                  <button
                    key={idx}
                    type="button"
                    className="example-pill-btn"
                    onClick={() => {
                      setQuery(q);
                      onSearch(q);
                    }}
                    disabled={loading}
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
