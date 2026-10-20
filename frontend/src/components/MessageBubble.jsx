import React from 'react';
import { motion } from 'framer-motion';
import { Clock } from 'lucide-react';
import { MessageResponse } from './MessageResponse';
import { markdownComponents, parseCitations } from './MarkdownRenderer';
import ReactMarkdown from 'react-markdown';

const springConfig = { type: 'spring', stiffness: 300, damping: 30, mass: 1 };

export function MessageBubble({ message, onSelectCitation, isLast, isStreaming = false }) {
  const isUser = message.role === 'user';
  const isLoading = message.loading === true;
  const hasError = !!message.error;
  const content = message.content;

  if (isUser) {
    return (
      <motion.div
        className="message-bubble user"
        role="listitem"
        initial={{ opacity: 0, y: 20, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={springConfig}
        style={{
          display: 'flex',
          justifyContent: 'flex-end',
          margin: 'var(--space-3) 0',
          paddingRight: 'var(--space-4)',
        }}
      >
        <div
          className="message-content user-content"
          style={{
            maxWidth: '80%',
            background: 'var(--accent-blue)',
            color: 'var(--fg-inverse)',
            borderRadius: '18px 18px 4px 18px',
            padding: 'var(--space-3) var(--space-4)',
            boxShadow: 'var(--shadow-sm)',
          }}
        >
          <p style={{ margin: 0, lineHeight: 'var(--leading-relaxed)', wordWrap: 'break-word' }}>
            {message.content}
          </p>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 'var(--space-2)', marginTop: 'var(--space-2)' }}>
            <time
              style={{
                fontSize: 'var(--text-xs)',
                color: 'rgba(255,255,255,0.7)',
                fontFamily: 'var(--font-mono)',
                fontVariantNumeric: 'tabular-nums',
              }}
              dateTime={new Date(message.timestamp).toISOString()}
            >
              {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </time>
          </div>
        </div>
      </motion.div>
    );
  }

  // Assistant message
  return (
    <motion.div
      className={`message-bubble assistant ${isLoading ? 'loading' : ''}`}
      role="listitem"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={springConfig}
      style={{
        display: 'flex',
        justifyContent: 'flex-start',
        margin: 'var(--space-3) 0',
        paddingLeft: 'var(--space-4)',
      }}
    >
      <div
        className="message-content assistant-content"
        style={{
          maxWidth: '85%',
          background: 'var(--glass-light)',
          backdropFilter: 'blur(var(--glass-blur)) saturate(180%)',
          WebkitBackdropFilter: 'blur(var(--glass-blur)) saturate(180%)',
          border: '1px solid var(--glass-border)',
          borderRadius: '18px 18px 18px 4px',
          padding: 'var(--space-3) var(--space-4)',
          boxShadow: 'var(--shadow-sm)',
        }}
      >
        {isLoading && (
          <LoadingIndicator mode={message.mode} />
        )}

        {hasError && (
          <ErrorMessage error={message.error} />
        )}

        {!isLoading && !hasError && content && (
          <MessageResponse
            response={content}
            mode={message.mode}
            onSelectCitation={onSelectCitation}
          />
        )}

        {!isLoading && !hasError && !content && (
          <p style={{ color: 'var(--fg-tertiary)', fontStyle: 'italic', margin: 0 }}>
            No response received.
          </p>
        )}

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-start', gap: 'var(--space-2)', marginTop: 'var(--space-2)' }}>
          <time
            style={{
              fontSize: 'var(--text-xs)',
              color: 'var(--fg-tertiary)',
              fontFamily: 'var(--font-mono)',
              fontVariantNumeric: 'tabular-nums',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
            }}
            dateTime={new Date(message.timestamp).toISOString()}
          >
            <Clock size={10} aria-hidden="true" style={{ color: 'var(--fg-quaternary)' }} />
            {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </time>
        </div>
      </div>
    </motion.div>
  );
}

function LoadingIndicator({ mode }) {
  const messages = {
    compare: 'Running dual execution: Vector Baseline vs Hybrid KG-RAG...',
    vector: 'Executing vector baseline retrieval...',
    graph: 'Traversing knowledge graph...',
    hybrid: 'Executing hybrid retrieval & grounded generation...',
    auto: 'Executing retrieval & grounded generation...',
  };

  return (
    <motion.div
      className="loading-indicator"
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 'var(--space-3)',
        padding: 'var(--space-4)',
      }}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
    >
      <div className="loading-orbit" style={{ position: 'relative', width: '56px', height: '56px' }}>
        <motion.div
          className="orbit-spinner"
          style={{
            position: 'absolute',
            inset: 0,
            border: '3px solid rgba(0, 113, 227, 0.15)',
            borderTopColor: 'var(--accent-blue)',
            borderRadius: '50%',
          }}
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
        />
        <motion.div
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--accent-blue)',
          }}
          animate={{ scale: [1, 1.1, 1] }}
          transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
          </svg>
        </motion.div>
      </div>
      <span style={{ fontSize: 'var(--text-sm)', color: 'var(--fg-secondary)', textAlign: 'center' }}>
        {messages[mode] || messages.auto}
      </span>
    </motion.div>
  );
}

function ErrorMessage({ error }) {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-3)',
        padding: 'var(--space-4)',
        background: 'var(--accent-red-weak)',
        border: '1px solid rgba(255, 59, 48, 0.3)',
        borderRadius: 'var(--radius-lg)',
        color: 'var(--accent-red)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 'var(--space-3)' }}>
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0, marginTop: '2px' }}>
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="8" x2="12" y2="12" />
          <line x1="12" y1="16" x2="12.01" y2="16" />
        </svg>
        <div style={{ flex: 1 }}>
          <p style={{ margin: 0, fontWeight: 500 }}>Error</p>
          <p style={{ margin: 'var(--space-1) 0 0', fontSize: 'var(--text-sm)', color: 'var(--fg-secondary)' }}>
            {error}
          </p>
        </div>
      </div>
      <button
        onClick={() => window.location.reload()}
        style={{
          alignSelf: 'flex-start',
          padding: 'var(--space-2) var(--space-4)',
          background: 'var(--accent-red)',
          color: 'white',
          border: 'none',
          borderRadius: 'var(--radius-md)',
          fontSize: 'var(--text-sm)',
          fontWeight: 500,
          cursor: 'pointer',
          fontFamily: 'var(--font-system)',
        }}
      >
        Retry
      </button>
    </div>
  );
}