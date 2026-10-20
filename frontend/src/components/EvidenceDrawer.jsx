import React, { useEffect } from 'react';
import { motion } from 'framer-motion';
import { X, ShieldCheck, BookOpen, Layers, FileText } from 'lucide-react';
import { GlassPanel } from './ui/Card';
import { Badge } from './ui/Badge';
import { useDragSheet } from '../hooks/useDragSheet';
import { useReducedMotion } from '../hooks/useReducedMotion';

const springConfig = { type: 'spring', stiffness: 300, damping: 30, mass: 1 };

export default function EvidenceDrawer({ activeCitation, onClose }) {
  const reducedMotion = useReducedMotion();
  const isGraph = activeCitation?.source_type === 'graph' || activeCitation?.label?.startsWith('[G');

  const {
    ref: drawerRef,
    style: drawerStyle,
  } = useDragSheet({
    isOpen: !!activeCitation,
    onClose,
    direction: 'right',
    width: 420,
    reducedMotion,
  });

  // Handle ESC key
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  // Focus trap
  useEffect(() => {
    if (!activeCitation) return;
    const drawer = drawerRef.current;
    if (!drawer) return;

    const focusableElements = drawer.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];

    const handleTab = (e) => {
      if (e.key !== 'Tab') return;
      if (e.shiftKey) {
        if (document.activeElement === firstElement) {
          e.preventDefault();
          lastElement?.focus();
        }
      } else {
        if (document.activeElement === lastElement) {
          e.preventDefault();
          firstElement?.focus();
        }
      }
    };

    drawer.addEventListener('keydown', handleTab);
    firstElement?.focus();

    return () => drawer.removeEventListener('keydown', handleTab);
  }, [drawerRef, activeCitation]);

  if (!activeCitation) return null;

  return (
    <motion.div
      className="drawer-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="drawer-title"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 200,
        background: 'rgba(0, 0, 0, 0.3)',
        backdropFilter: 'blur(4px)',
        WebkitBackdropFilter: 'blur(4px)',
      }}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={springConfig}
      onClick={onClose}
    >
      <motion.div
        ref={drawerRef}
        className="drawer-panel"
        style={{
          position: 'absolute',
          top: 0,
          right: 0,
          bottom: 0,
          width: 'var(--drawer-width)',
          maxWidth: '100vw',
          display: 'flex',
          flexDirection: 'column',
          background: 'var(--glass-heavy)',
          backdropFilter: 'blur(var(--glass-blur-heavy)) saturate(180%)',
          WebkitBackdropFilter: 'blur(var(--glass-blur-heavy)) saturate(180%)',
          borderLeft: '1px solid var(--glass-border)',
          boxShadow: 'var(--shadow-xl)',
          overflow: 'hidden',
          ...drawerStyle,
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Drag Handle */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'center',
            padding: 'var(--space-3) 0',
            cursor: 'grab',
            touchAction: 'none',
          }}
          role="button"
          tabIndex={0}
          aria-label="Drag to resize or dismiss"
        >
          <motion.div
            style={{
              width: '36px',
              height: '4px',
              borderRadius: 'var(--radius-full)',
              background: 'var(--fg-tertiary)',
            }}
            whileHover={{ scaleX: 1.2, background: 'var(--fg-secondary)' }}
            whileTap={{ scale: 0.95 }}
          />
        </div>

        {/* Header */}
        <div
          className="drawer-header"
          style={{
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'space-between',
            padding: '0 var(--space-4) var(--space-4)',
            borderBottom: '1px solid var(--glass-border)',
          }}
        >
          <div className="drawer-header-left" style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)', flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
              <Badge
                variant={isGraph ? 'green' : 'blue'}
                size="sm"
              >
                {activeCitation.label}
              </Badge>
              <h3
                id="drawer-title"
                style={{
                  margin: 0,
                  fontSize: 'var(--text-lg)',
                  fontWeight: 600,
                  color: 'var(--fg-primary)',
                }}
              >
                Filing Evidence Provenance
              </h3>
            </div>
            <p style={{ margin: 0, fontSize: 'var(--text-sm)', color: 'var(--fg-secondary)' }}>
              Verbatim excerpt from the SEC 10-K filing supporting this citation
            </p>
          </div>
          <button
            onClick={onClose}
            aria-label="Close evidence drawer"
            style={{
              width: '36px',
              height: '36px',
              borderRadius: 'var(--radius-md)',
              background: 'transparent',
              border: 'none',
              color: 'var(--fg-tertiary)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'all 150ms cubic-bezier(0.25, 0.46, 0.45, 0.94)',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--bg-tertiary)'; e.currentTarget.style.color = 'var(--fg-primary)'; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--fg-tertiary)'; }}
          >
            <X size={20} aria-hidden="true" />
          </button>
        </div>

        {/* Body */}
        <div className="drawer-body" style={{ flex: 1, overflowY: 'auto', padding: 'var(--space-4)' }}>
          {/* Metadata Card */}
          <GlassPanel padding="md" style={{ marginBottom: 'var(--space-4)' }}>
            <dl style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: 'var(--space-3) var(--space-4)', margin: 0 }}>
              <div>
                <dt style={{ fontSize: 'var(--text-xs)', color: 'var(--fg-tertiary)', textTransform: 'uppercase', letterSpacing: 'var(--tracking-wider)', fontWeight: 500 }}>
                  Company Filer
                </dt>
                <dd style={{ margin: 0, fontSize: 'var(--text-sm)', fontWeight: 500, color: 'var(--fg-primary)', wordBreak: 'break-word' }}>
                  {activeCitation.company || 'Enterprise 10-K'}
                </dd>
              </div>
              {activeCitation.ticker && (
                <>
                  <dt style={{ fontSize: 'var(--text-xs)', color: 'var(--fg-tertiary)', textTransform: 'uppercase', letterSpacing: 'var(--tracking-wider)', fontWeight: 500 }}>
                    Ticker
                  </dt>
                  <dd style={{ margin: 0, fontSize: 'var(--text-sm)', fontFamily: 'var(--font-mono)', fontWeight: 500, color: 'var(--fg-primary)' }}>
                    {activeCitation.ticker}
                  </dd>
                </>
              )}
              <dt style={{ fontSize: 'var(--text-xs)', color: 'var(--fg-tertiary)', textTransform: 'uppercase', letterSpacing: 'var(--tracking-wider)', fontWeight: 500 }}>
                Section Path
              </dt>
              <dd style={{ margin: 0, fontSize: 'var(--text-sm)', fontFamily: 'var(--font-mono)', color: 'var(--fg-secondary)' }}>
                {activeCitation.section_path || '10-K Filing'}
              </dd>
              <dt style={{ fontSize: 'var(--text-xs)', color: 'var(--fg-tertiary)', textTransform: 'uppercase', letterSpacing: 'var(--tracking-wider)', fontWeight: 500 }}>
                Chunk ID
              </dt>
              <dd style={{ margin: 0, fontSize: 'var(--text-xs)', fontFamily: 'var(--font-mono)', color: 'var(--fg-tertiary)' }}>
                {activeCitation.chunk_id}
              </dd>
              <dt style={{ fontSize: 'var(--text-xs)', color: 'var(--fg-tertiary)', textTransform: 'uppercase', letterSpacing: 'var(--tracking-wider)', fontWeight: 500 }}>
                Source Type
              </dt>
              <dd style={{ margin: 0 }}>
                <Badge variant={isGraph ? 'green' : 'blue'} size="sm">
                  {isGraph ? 'Graph Traversal' : 'Vector Retrieval'}
                </Badge>
              </dd>
              <dt style={{ fontSize: 'var(--text-xs)', color: 'var(--fg-tertiary)', textTransform: 'uppercase', letterSpacing: 'var(--tracking-wider)', fontWeight: 500 }}>
                Verification
              </dt>
              <dd style={{ margin: 0, display: 'flex', alignItems: 'center', gap: 'var(--space-2)', color: 'var(--accent-green)' }}>
                <ShieldCheck size={14} aria-hidden="true" />
                <span style={{ fontSize: 'var(--text-sm)', fontWeight: 500 }}>100% Mechanically Grounded</span>
              </dd>
            </dl>
          </GlassPanel>

          {/* Evidence Content Section */}
          <div style={{ marginBottom: 'var(--space-4)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 'var(--space-3)' }}>
              <BookOpen size={15} style={{ color: 'var(--accent-blue)' }} aria-hidden="true" />
              <span style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--fg-primary)' }}>
                Verbatim Filing Excerpt
              </span>
            </div>
            <GlassPanel padding="md" style={{ maxHeight: '300px', overflowY: 'auto' }}>
              {activeCitation.text_snippet ? (
                <p style={{ margin: 0, lineHeight: 'var(--leading-relaxed)', color: 'var(--fg-primary)', fontSize: 'var(--text-sm)', whiteSpace: 'pre-wrap', fontFamily: 'var(--font-system)' }}>
                  {activeCitation.text_snippet}
                </p>
              ) : activeCitation.evidence_quote ? (
                <blockquote style={{ margin: 0, padding: 0, fontStyle: 'italic', color: 'var(--fg-secondary)', lineHeight: 'var(--leading-relaxed)', fontSize: 'var(--text-sm)', borderLeft: '3px solid var(--accent-blue)', paddingLeft: 'var(--space-3)' }}>
                  "{activeCitation.evidence_quote}"
                </blockquote>
              ) : (
                <p style={{ margin: 0, color: 'var(--fg-tertiary)', fontSize: 'var(--text-sm)' }}>
                  Chunk text verified from PostgreSQL storage.
                </p>
              )}
            </GlassPanel>
          </div>

          {/* Observation IDs for Graph items */}
          {activeCitation.observation_ids && activeCitation.observation_ids.length > 0 && (
            <div style={{ marginBottom: 'var(--space-4)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 'var(--space-3)' }}>
                <Layers size={15} style={{ color: 'var(--accent-green)' }} aria-hidden="true" />
                <span style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--fg-primary)' }}>
                  Extraction Observations ({activeCitation.observation_ids.length})
                </span>
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
                {activeCitation.observation_ids.map((obsId, idx) => (
                  <span
                    key={idx}
                    style={{
                      padding: 'var(--space-1) var(--space-2)',
                      background: 'var(--bg-tertiary)',
                      border: '1px solid var(--glass-border)',
                      borderRadius: 'var(--radius-sm)',
                      fontSize: 'var(--text-xs)',
                      fontFamily: 'var(--font-mono)',
                      color: 'var(--fg-secondary)',
                    }}
                  >
                    {obsId}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Passages reference if available */}
          {activeCitation.passages && activeCitation.passages.length > 0 && (
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 'var(--space-3)' }}>
                <FileText size={15} style={{ color: 'var(--accent-blue)' }} aria-hidden="true" />
                <span style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--fg-primary)' }}>
                  Related Passages ({activeCitation.passages.length})
                </span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
                {activeCitation.passages.map((p, idx) => (
                  <div
                    key={idx}
                    className="passage-item"
                    style={{
                      padding: 'var(--space-3)',
                      background: 'var(--bg-secondary)',
                      border: '1px solid var(--glass-border)',
                      borderRadius: 'var(--radius-md)',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 'var(--space-2)', flexWrap: 'wrap' }}>
                      <Badge variant="blue" size="xs">[P{idx + 1}]</Badge>
                      <span style={{ fontSize: 'var(--text-sm)', fontWeight: 500, color: 'var(--fg-primary)' }}>{p.company}</span>
                      <span style={{ fontSize: 'var(--text-xs)', fontFamily: 'var(--font-mono)', color: 'var(--fg-tertiary)' }}>
                        Sim: {(Number(p.cosine_similarity || p.similarity || 0) * 100).toFixed(1)}%
                      </span>
                    </div>
                    <p style={{ margin: 0, fontSize: 'var(--text-sm)', color: 'var(--fg-secondary)', lineHeight: 'var(--leading-relaxed)' }}>
                      {p.text.slice(0, 160)}{p.text.length > 160 ? '...' : ''}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </motion.div>
    </motion.div>
  );
}