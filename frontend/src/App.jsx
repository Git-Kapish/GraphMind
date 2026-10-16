import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import QueryHero from './components/QueryHero';
import ResponseView from './components/ResponseView';
import CompareView from './components/CompareView';
import EvidenceDrawer from './components/EvidenceDrawer';
import BenchmarkModal from './components/BenchmarkModal';

export default function App() {
  const [query, setQuery] = useState('');
  const [mode, setMode] = useState('auto');
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState(null);
  const [compareData, setCompareData] = useState(null);
  const [activeCitation, setActiveCitation] = useState(null);
  const [isBenchmarkOpen, setIsBenchmarkOpen] = useState(false);
  const [health, setHealth] = useState(null);
  const [error, setError] = useState(null);

  // Fetch API and database health status on load
  useEffect(() => {
    async function fetchHealth() {
      try {
        const res = await fetch('/health');
        if (res.ok) {
          const data = await res.json();
          setHealth(data);
        }
      } catch (err) {
        console.warn('Backend /health unreachable on initial load:', err);
      }
    }
    fetchHealth();
  }, []);

  const handleSearch = async (searchQuery) => {
    const q = searchQuery || query;
    if (!q.trim()) return;

    setLoading(true);
    setError(null);

    try {
      if (mode === 'compare') {
        // Dual parallel execution for Side-by-Side comparison
        const [baselineRes, hybridRes] = await Promise.all([
          fetch('/query/baseline', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question: q, top_k: 5, debug: true }),
          }),
          fetch('/query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question: q, mode: 'auto', top_k: 5, debug: true }),
          }),
        ]);

        const baselineJson = baselineRes.ok ? await baselineRes.json() : null;
        const hybridJson = hybridRes.ok ? await hybridRes.json() : null;

        setCompareData({
          baseline: baselineJson,
          hybrid: hybridJson,
        });
        setResponse(null);
      } else if (mode === 'vector') {
        // Plain Vector Baseline
        const res = await fetch('/query/baseline', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ question: q, top_k: 5, debug: true }),
        });
        if (!res.ok) throw new Error(`Server returned status ${res.status}`);
        const data = await res.json();
        setResponse(data);
        setCompareData(null);
      } else {
        // Auto-Routed, Graph-Only, or Forced Hybrid
        const res = await fetch('/query', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ question: q, mode, top_k: 5, debug: true }),
        });
        if (!res.ok) throw new Error(`Server returned status ${res.status}`);
        const data = await res.json();
        setResponse(data);
        setCompareData(null);
      }
    } catch (err) {
      console.error('Query execution error:', err);
      setError(err.message || 'An error occurred during query execution.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-layout">
      {/* Top Navigation */}
      <Navbar
        health={health}
        onOpenBenchmark={() => setIsBenchmarkOpen(true)}
      />

      {/* Main Content Area */}
      <main className="main-content">
        <QueryHero
          query={query}
          setQuery={setQuery}
          mode={mode}
          setMode={setMode}
          onSearch={handleSearch}
          loading={loading}
        />

        {error && (
          <div className="error-banner glass-panel fade-in">
            <strong>Error:</strong> {error}
          </div>
        )}

        {mode === 'compare' ? (
          <CompareView
            baselineData={compareData?.baseline}
            hybridData={compareData?.hybrid}
            loading={loading}
            onSelectCitation={setActiveCitation}
          />
        ) : (
          <ResponseView
            response={response}
            loading={loading}
            onSelectCitation={setActiveCitation}
          />
        )}
      </main>

      {/* Slide-in Evidence Drawer */}
      <EvidenceDrawer
        activeCitation={activeCitation}
        onClose={() => setActiveCitation(null)}
      />

      {/* Benchmark Summary Modal */}
      <BenchmarkModal
        isOpen={isBenchmarkOpen}
        onClose={() => setIsBenchmarkOpen(false)}
      />
    </div>
  );
}
