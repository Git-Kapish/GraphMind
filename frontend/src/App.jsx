import React, { useState, useEffect, useRef, useCallback } from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import TopBar from './components/TopBar';
import ChatInterface from './components/ChatInterface';
import BenchmarkPage from './components/BenchmarkPage';
import EvidenceDrawer from './components/EvidenceDrawer';

export default function App() {
  const [messages, setMessages] = useState([]);
  const [mode, setMode] = useState('auto');
  const [health, setHealth] = useState(null);
  const [activeCitation, setActiveCitation] = useState(null);
  const messagesEndRef = useRef(null);
  const chatContainerRef = useRef(null);

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

  // Auto-scroll to bottom when messages change
  const scrollToBottom = useCallback(() => {
    if (messagesEndRef.current) {
      const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      messagesEndRef.current.scrollIntoView({ behavior: prefersReducedMotion ? 'auto' : 'smooth' });
    }
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const handleSearch = async (searchQuery, currentMode) => {
    const q = searchQuery.trim();
    if (!q) return;

    // Add user message immediately
    const userMessage = { role: 'user', content: q, timestamp: Date.now() };
    setMessages(prev => [...prev, userMessage]);

    // Optimistic assistant message with loading state
    const assistantMessageId = Date.now();
    const loadingMessage = {
      id: assistantMessageId,
      role: 'assistant',
      content: null,
      loading: true,
      mode: currentMode,
      timestamp: Date.now()
    };
    setMessages(prev => [...prev, loadingMessage]);

    try {
      let responseData = null;
      let compareData = null;

      if (currentMode === 'compare') {
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

        compareData = {
          baseline: baselineJson,
          hybrid: hybridJson,
        };
      } else if (currentMode === 'vector') {
        // Plain Vector Baseline
        const res = await fetch('/query/baseline', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ question: q, top_k: 5, debug: true }),
        });
        if (!res.ok) throw new Error(`Server returned status ${res.status}`);
        responseData = await res.json();
      } else {
        // Auto-Routed, Graph-Only, or Forced Hybrid
        const res = await fetch('/query', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ question: q, mode: currentMode, top_k: 5, debug: true }),
        });
        if (!res.ok) throw new Error(`Server returned status ${res.status}`);
        responseData = await res.json();
      }

      // Replace loading message with actual response
      setMessages(prev => prev.map(msg =>
        msg.id === assistantMessageId
          ? {
              ...msg,
              loading: false,
              content: currentMode === 'compare' ? compareData : responseData,
              mode: currentMode
            }
          : msg
      ));
    } catch (err) {
      console.error('Query execution error:', err);
      setMessages(prev => prev.map(msg =>
        msg.id === assistantMessageId
          ? {
              ...msg,
              loading: false,
              error: err.message || 'An error occurred during query execution.',
              mode: currentMode
            }
          : msg
      ));
    }
  };

  const handleSelectCitation = useCallback((citation) => {
    setActiveCitation(citation);
  }, []);

  const handleCloseDrawer = useCallback(() => {
    setActiveCitation(null);
  }, []);

  return (
    <Router>
      <div className="app-layout">
        {/* Minimal Top Bar */}
        <TopBar health={health} />

        {/* Routes */}
        <main className="main-content">
          <Routes>
            <Route path="/" element={
              <ChatInterface
                messages={messages}
                mode={mode}
                setMode={setMode}
                onSearch={handleSearch}
                onSelectCitation={handleSelectCitation}
                messagesEndRef={messagesEndRef}
                chatContainerRef={chatContainerRef}
              />
            } />
            <Route path="/benchmark" element={<BenchmarkPage />} />
          </Routes>
        </main>

        {/* Slide-in Evidence Drawer */}
        <EvidenceDrawer
          activeCitation={activeCitation}
          onClose={handleCloseDrawer}
        />
      </div>
    </Router>
  );
}