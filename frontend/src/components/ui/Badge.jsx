import React from 'react';

export function Badge({
  children,
  variant = 'subtle',
  size = 'md',
  className = '',
  style = {},
  ...props
}) {
  const variants = {
    blue: { background: 'var(--accent-blue-weak)', color: 'var(--accent-blue)', border: '1px solid rgba(0, 113, 227, 0.2)' },
    green: { background: 'var(--accent-green-weak)', color: 'var(--accent-green)', border: '1px solid rgba(52, 199, 89, 0.2)' },
    orange: { background: 'var(--accent-orange-weak)', color: 'var(--accent-orange)', border: '1px solid rgba(255, 159, 10, 0.2)' },
    red: { background: 'var(--accent-red-weak)', color: 'var(--accent-red)', border: '1px solid rgba(255, 59, 48, 0.2)' },
    purple: { background: 'rgba(175, 82, 222, 0.1)', color: 'var(--accent-purple)', border: '1px solid rgba(175, 82, 222, 0.2)' },
    pink: { background: 'rgba(255, 45, 146, 0.1)', color: 'var(--accent-pink)', border: '1px solid rgba(255, 45, 146, 0.2)' },
    subtle: { background: 'var(--bg-tertiary)', color: 'var(--fg-secondary)', border: '1px solid var(--glass-border)' },
  };

  const sizes = {
    xs: { fontSize: 'var(--text-xs)', padding: '2px 6px', gap: '4px' },
    sm: { fontSize: 'var(--text-xs)', padding: '3px 8px', gap: '4px' },
    md: { fontSize: 'var(--text-xs)', padding: '4px 10px', gap: '6px' },
  };

  return (
    <span
      className={className}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        borderRadius: 'var(--radius-full)',
        fontFamily: 'var(--font-system)',
        fontWeight: 600,
        letterSpacing: 'var(--tracking-wider)',
        textTransform: 'uppercase',
        whiteSpace: 'nowrap',
        ...variants[variant],
        ...sizes[size],
        ...style,
      }}
      {...props}
    >
      {children}
    </span>
  );
}

// Citation badge specifically for inline citations
export function CitationBadge({
  children,
  sourceType = 'vector', // 'graph' | 'vector'
  onClick,
  className = '',
  ...props
}) {
  const isGraph = sourceType === 'graph';

  return (
    <button
      type="button"
      onClick={onClick}
      className={className}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        margin: '0 2px',
        padding: '2px 6px',
        borderRadius: 'var(--radius-sm)',
        fontFamily: 'var(--font-mono)',
        fontSize: '0.75rem',
        fontWeight: 600,
        cursor: 'pointer',
        transition: 'all 150ms cubic-bezier(0.25, 0.46, 0.45, 0.94)',
        verticalAlign: 'baseline',
        textDecoration: 'none',
        border: '1px solid transparent',
        background: isGraph ? 'var(--accent-green-weak)' : 'var(--accent-blue-weak)',
        color: isGraph ? 'var(--accent-green)' : 'var(--accent-blue)',
        borderColor: isGraph ? 'rgba(52, 199, 89, 0.3)' : 'rgba(0, 113, 227, 0.3)',
        ...props,
      }}
      whileHover={{ transform: 'translateY(-1px)', boxShadow: isGraph ? '0 0 12px var(--accent-green-weak)' : '0 0 12px var(--accent-blue-weak)' }}
      whileTap={{ transform: 'translateY(0)' }}
    >
      {children}
    </button>
  );
}