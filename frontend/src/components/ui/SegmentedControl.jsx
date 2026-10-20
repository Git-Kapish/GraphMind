import React from 'react';
import { motion } from 'framer-motion';

const springConfig = { type: 'spring', stiffness: 300, damping: 30, mass: 1 };

export function SegmentedControl({
  options,
  value,
  onChange,
  size = 'md',
  className = '',
  'aria-label': ariaLabel,
  disabled = false,
}) {
  const sizes = {
    sm: { padding: '2px', itemPadding: '6px 12px', fontSize: 'var(--text-xs)', borderRadius: 'calc(var(--radius-md) - 2px)' },
    md: { padding: '2px', itemPadding: '8px 16px', fontSize: 'var(--text-sm)', borderRadius: 'calc(var(--radius-md) - 2px)' },
    lg: { padding: '3px', itemPadding: '10px 20px', fontSize: 'var(--text-base)', borderRadius: 'calc(var(--radius-lg) - 3px)' },
  };

  const s = sizes[size];

  return (
    <div
      role="group"
      aria-label={ariaLabel}
      className={className}
      style={{
        display: 'inline-flex',
        background: 'var(--bg-tertiary)',
        border: '1px solid var(--glass-border)',
        borderRadius: 'var(--radius-md)',
        padding: s.padding,
      }}
    >
      {options.map((option, index) => (
        <motion.button
          key={option.value}
          type="button"
          role="radio"
          aria-checked={value === option.value}
          aria-disabled={disabled}
          disabled={disabled}
          onClick={() => !disabled && onChange(option.value)}
          style={{
            padding: s.itemPadding,
            fontFamily: 'var(--font-system)',
            fontSize: s.fontSize,
            fontWeight: 500,
            color: value === option.value ? 'var(--fg-inverse)' : 'var(--fg-secondary)',
            borderRadius: s.borderRadius,
            border: 'none',
            background: value === option.value ? 'var(--accent-blue)' : 'transparent',
            cursor: disabled ? 'not-allowed' : 'pointer',
            whiteSpace: 'nowrap',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            opacity: disabled ? 0.4 : 1,
          }}
          whileHover={!disabled && value !== option.value ? { background: 'var(--bg-quaternary)', color: 'var(--fg-primary)' } : {}}
          whileTap={{ scale: 0.98 }}
          transition={springConfig}
        >
          {option.icon && <span aria-hidden="true">{option.icon}</span>}
          {option.label}
        </motion.button>
      ))}
    </div>
  );
}