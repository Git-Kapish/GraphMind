import React from 'react';
import { motion } from 'framer-motion';

const QUICK_PROMPTS = [
  { label: 'Multi-hop', question: "Which subsidiaries of AMD operate in Singapore according to Exhibit 21?" },
  { label: 'Two-hop', question: "In what country does AMD's subsidiary Silo AI Oy operate?" },
  { label: 'Single-hop', question: "Who were the founders of Intel Corporation?" },
  { label: 'Refusal', question: "Who is the Chief Technology Officer of Tesla Inc.?" },
];

const springConfig = { type: 'spring', stiffness: 300, damping: 30, mass: 1 };

export function QuickPrompts({ onSelect, className = '' }) {
  return (
    <div className={className} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 'var(--space-2)' }}>
        <span style={{ fontSize: 'var(--text-xs)', color: 'var(--fg-tertiary)', textTransform: 'uppercase', letterSpacing: 'var(--tracking-wider)', fontWeight: 600 }}>
          Try asking
        </span>
        <div style={{ flex: 1, height: '1px', background: 'var(--glass-border)' }} />
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-2)', justifyContent: 'center' }}>
        {QUICK_PROMPTS.map(({ label, question }, index) => (
          <motion.button
            key={index}
            type="button"
            onClick={() => onSelect(question)}
            title={question}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 'var(--space-2)',
              padding: 'var(--space-2) var(--space-3)',
              background: 'var(--bg-tertiary)',
              border: '1px solid var(--glass-border)',
              borderRadius: 'var(--radius-full)',
              fontFamily: 'var(--font-system)',
              fontSize: 'var(--text-sm)',
              color: 'var(--fg-secondary)',
              cursor: 'pointer',
              whiteSpace: 'nowrap',
              transition: 'all 150ms cubic-bezier(0.25, 0.46, 0.45, 0.94)',
            }}
            whileHover={{ borderColor: 'var(--accent-blue)', color: 'var(--accent-blue)', background: 'var(--accent-blue-weak)' }}
            whileTap={{ scale: 0.97 }}
            transition={springConfig}
          >
            <span style={{
              fontSize: 'var(--text-xs)',
              fontWeight: 600,
              color: 'var(--fg-tertiary)',
              textTransform: 'uppercase',
              letterSpacing: 'var(--tracking-wider)',
            }}>
              {label}
            </span>
          </motion.button>
        ))}
      </div>
    </div>
  );
}