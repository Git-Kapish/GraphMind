import React from 'react';
import { motion } from 'framer-motion';

const springConfig = { type: 'spring', stiffness: 300, damping: 30, mass: 1 };
const pressSpring = { type: 'spring', stiffness: 500, damping: 40, mass: 0.5 };

export function Button({
  children,
  variant = 'primary',
  size = 'md',
  disabled = false,
  loading = false,
  leftIcon,
  rightIcon,
  fullWidth = false,
  className = '',
  onClick,
  type = 'button',
  'aria-label': ariaLabel,
  ...props
}) {
  const baseStyles = {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '8px',
    fontFamily: 'var(--font-system)',
    fontWeight: 500,
    borderRadius: 'var(--radius-md)',
    border: 'none',
    cursor: disabled ? 'not-allowed' : 'pointer',
    transition: 'all 150ms cubic-bezier(0.25, 0.46, 0.45, 0.94)',
    textDecoration: 'none',
    whiteSpace: 'nowrap',
    width: fullWidth ? '100%' : 'auto',
  };

  const variants = {
    primary: {
      background: 'var(--accent-blue)',
      color: 'var(--fg-inverse)',
      padding: '10px 20px',
      height: '40px',
    },
    secondary: {
      background: 'var(--bg-tertiary)',
      color: 'var(--fg-primary)',
      border: '1px solid var(--glass-border)',
      padding: '10px 20px',
      height: '40px',
    },
    ghost: {
      background: 'transparent',
      color: 'var(--fg-secondary)',
      padding: '8px 16px',
      height: '36px',
    },
    danger: {
      background: 'var(--accent-red)',
      color: 'var(--fg-inverse)',
      padding: '10px 20px',
      height: '40px',
    },
  };

  const sizes = {
    sm: { fontSize: 'var(--text-xs)', padding: '6px 12px', height: '32px', gap: '6px' },
    md: { fontSize: 'var(--text-sm)', padding: '10px 20px', height: '40px', gap: '8px' },
    lg: { fontSize: 'var(--text-base)', padding: '12px 24px', height: '48px', gap: '10px' },
  };

  const style = {
    ...baseStyles,
    ...variants[variant],
    ...sizes[size],
    opacity: disabled || loading ? 0.4 : 1,
  };

  const hoverStyles = {
    primary: { background: 'var(--accent-blue-hover)', boxShadow: 'var(--shadow-md)', transform: 'translateY(-1px)' },
    secondary: { background: 'var(--bg-quaternary)', borderColor: 'var(--glass-border-strong)' },
    ghost: { background: 'var(--bg-tertiary)', color: 'var(--fg-primary)' },
    danger: { background: 'var(--accent-red-hover)', boxShadow: 'var(--shadow-md)', transform: 'translateY(-1px)' },
  };

  const activeStyles = {
    primary: { transform: 'translateY(0)', boxShadow: 'var(--shadow-sm)' },
    secondary: { transform: 'translateY(0)' },
    ghost: { transform: 'translateY(0)' },
    danger: { transform: 'translateY(0)', boxShadow: 'var(--shadow-sm)' },
  };

  return (
    <motion.button
      type={type}
      disabled={disabled || loading}
      onClick={onClick}
      aria-label={ariaLabel}
      aria-disabled={disabled || loading}
      aria-busy={loading}
      className={className}
      style={style}
      whileHover={disabled || loading ? {} : hoverStyles[variant]}
      whileTap={disabled || loading ? {} : activeStyles[variant]}
      transition={springConfig}
      {...props}
    >
      {loading ? (
        <span className="spinner" style={{ width: '16px', height: '16px', borderWidth: '2px' }} aria-hidden="true" />
      ) : (
        <>
          {leftIcon && <span aria-hidden="true">{leftIcon}</span>}
          {children}
          {rightIcon && <span aria-hidden="true">{rightIcon}</span>}
        </>
      )}
    </motion.button>
  );
}

export function IconButton({
  children,
  variant = 'ghost',
  size = 'md',
  disabled = false,
  className = '',
  onClick,
  'aria-label': ariaLabel,
  ...props
}) {
  const sizes = {
    sm: { width: '32px', height: '32px', borderRadius: 'var(--radius-sm)' },
    md: { width: '40px', height: '40px', borderRadius: 'var(--radius-md)' },
    lg: { width: '48px', height: '48px', borderRadius: 'var(--radius-lg)' },
  };

  const variants = {
    ghost: { background: 'transparent', color: 'var(--fg-secondary)' },
    subtle: { background: 'var(--bg-tertiary)', color: 'var(--fg-primary)' },
  };

  const hoverStyles = {
    ghost: { background: 'var(--bg-tertiary)', color: 'var(--fg-primary)' },
    subtle: { background: 'var(--bg-quaternary)' },
  };

  return (
    <motion.button
      disabled={disabled}
      onClick={onClick}
      aria-label={ariaLabel}
      aria-disabled={disabled}
      className={className}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        border: 'none',
        cursor: disabled ? 'not-allowed' : 'pointer',
        padding: 0,
        opacity: disabled ? 0.4 : 1,
        ...sizes[size],
        ...variants[variant],
      }}
      whileHover={disabled ? {} : hoverStyles[variant]}
      whileTap={{ scale: 0.95 }}
      transition={springConfig}
      {...props}
    >
      {children}
    </motion.button>
  );
}