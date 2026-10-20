import React from 'react';
import { motion } from 'framer-motion';
import { Sparkles, Database, Network, GitMerge, Zap } from 'lucide-react';
import { SegmentedControl } from './ui/SegmentedControl';
import { Textarea } from './ui/Input';
import { Button } from './ui/Button';
import { QuickPrompts } from './QuickPrompts';
import { Send } from 'lucide-react';

const MODE_OPTIONS = [
  { value: 'auto', label: 'Auto', icon: <Sparkles size={14} />, title: 'Auto-Routed Hybrid (recommended)' },
  { value: 'compare', label: 'Compare', icon: <GitMerge size={14} />, title: 'Side-by-Side: Vector vs Hybrid' },
  { value: 'vector', label: 'Vector', icon: <Database size={14} />, title: 'Dense Vector Baseline Only' },
  { value: 'graph', label: 'Graph', icon: <Network size={14} />, title: 'Knowledge Graph Only' },
  { value: 'hybrid', label: 'Hybrid', icon: <Zap size={14} />, title: 'Forced Hybrid (Graph + Vector)' },
];

const springConfig = { type: 'spring', stiffness: 300, damping: 30, mass: 1 };

export function EmptyState({
  mode,
  setMode,
  inputValue,
  setInputValue,
  onSubmit,
  inputRef,
}) {
  return (
    <motion.div
      className="empty-state"
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: 'calc(100vh - var(--topbar-height) - 120px)',
        padding: 'var(--space-8)',
        textAlign: 'center',
        maxWidth: 'var(--chat-max-width)',
        width: '100%',
        margin: '0 auto',
      }}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.25, 0.46, 0.45, 0.94] }}
    >
      {/* Header */}
      <div style={{ marginBottom: 'var(--space-8)' }}>
        <motion.h1
          style={{
            fontSize: 'var(--text-4xl)',
            fontWeight: 600,
            letterSpacing: 'var(--tracking-tight)',
            color: 'var(--fg-primary)',
            marginBottom: 'var(--space-3)',
            fontFamily: 'var(--font-system)',
          }}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, ...springConfig }}
        >
          GraphMind
        </motion.h1>
        <motion.p
          style={{
            fontSize: 'var(--text-lg)',
            color: 'var(--fg-secondary)',
            maxWidth: '480px',
            margin: '0 auto',
            lineHeight: 'var(--leading-relaxed)',
          }}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, ...springConfig }}
        >
          Ask about subsidiaries, ownership structures, executives, and financial relationships
          across 10 enterprise SEC 10-K filings.
        </motion.p>
      </div>

      {/* Mode Selector */}
      <motion.div
        style={{ width: '100%', maxWidth: '560px', marginBottom: 'var(--space-6)' }}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3, ...springConfig }}
      >
        <SegmentedControl
          options={MODE_OPTIONS}
          value={mode}
          onChange={setMode}
          size="lg"
          aria-label="Retrieval mode"
        />
      </motion.div>

      {/* Input Bar */}
      <motion.form
        onSubmit={onSubmit}
        style={{
          width: '100%',
          maxWidth: '560px',
          display: 'flex',
          gap: 'var(--space-3)',
          alignItems: 'flex-end',
        }}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4, ...springConfig }}
      >
        <Textarea
          ref={inputRef}
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          placeholder="Message GraphMind..."
          style={{
            flex: 1,
            minHeight: '56px',
            maxHeight: '200px',
            fontSize: 'var(--text-base)',
            padding: 'var(--space-3) var(--space-4)',
            borderRadius: 'var(--radius-lg)',
          }}
          aria-label="Enter your question"
        />
        <Button
          type="submit"
          variant="primary"
          size="lg"
          disabled={!inputValue.trim()}
          rightIcon={<Send size={18} />}
          aria-label="Send query"
          style={{
            height: '56px',
            borderRadius: 'var(--radius-lg)',
            flexShrink: 0,
          }}
        />
      </motion.form>

      {/* Quick Prompts */}
      <motion.div
        style={{ width: '100%', maxWidth: '560px', marginTop: 'var(--space-8)' }}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5, ...springConfig }}
      >
        <QuickPrompts onSelect={(q) => { setInputValue(q); onSubmit(new Event('submit')); }} />
      </motion.div>
    </motion.div>
  );
}