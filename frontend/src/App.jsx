import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import Navbar from './components/Navbar';
import QueryHero from './components/QueryHero';
import ResponseView from './components/ResponseView';
import CompareView from './components/CompareView';
import EvidenceDrawer from './components/EvidenceDrawer';
import BenchmarkPage from './components/BenchmarkPage';
import ProjectInfoPage from './components/ProjectInfoPage';

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
    <Router>
      <div className="app-layout">
        {/* Top Navigation with Links */}
        <Navbar
          health={health}
          onOpenBenchmark={() => setIsBenchmarkOpen(false)}
        />

        {/* Routes */}
        <main className="main-content">
          <Routes>
            <Route path="/" element={<QueryHero
              query={query}
              setQuery={setQuery}
              mode={mode}
              setMode={setMode}
              onSearch={handleSearch}
              loading={loading}
            />} />
            <Route path="/benchmark" element={<BenchmarkPage />} />
            <Route path="/project" element={<ProjectInfoPage />} />
          </Routes>
        </main>

        {/* Slide-in Evidence Drawer */}
        <EvidenceDrawer
          activeCitation={activeCitation}
          onClose={() => setActiveCitation(null)}
        />

        {/* Benchmark Summary Modal - hidden, navigation goes to page instead */}
        {/* <BenchmarkModal
          isOpen={isBenchmarkOpen}
          onClose={() => setIsBenchmarkOpen(false)}
        /> */}
      </div>
    </Router>
  );
}
