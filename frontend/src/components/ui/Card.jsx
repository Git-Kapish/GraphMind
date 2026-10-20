import React from 'react';

export function Card({
  children,
  variant = 'default', // 'default' | 'glass' | 'glass-heavy'
  padding = 'md', // 'none' | 'sm' | 'md' | 'lg'
  className = '',
  style = {},
  onClick,
  ...props
}) {
  const variants = {
    default: {
      background: 'var(--bg-elevated)',
      border: '1px solid var(--glass-border)',
      boxShadow: 'var(--shadow-sm)',
      hoverBorder: 'var(--glass-border-strong)',
      hoverShadow: 'var(--shadow-md)',
    },
    glass: {
      background: 'var(--glass-light)',
      backdropFilter: 'blur(var(--glass-blur)) saturate(180%)',
      border: '1px solid var(--glass-border)',
      boxShadow: 'var(--shadow-sm)',
      hoverBorder: 'var(--glass-border-strong)',
      hoverShadow: 'var(--shadow-md)',
    },
    'glass-heavy': {
      background: 'var(--glass-heavy)',
      backdropFilter: 'blur(var(--glass-blur-heavy)) saturate(180%)',
      border: '1px solid var(--glass-border)',
      boxShadow: 'var(--shadow-md)',
      hoverBorder: 'var(--glass-border-strong)',
      hoverShadow: 'var(--shadow-lg)',
    },
  };

  const paddings = {
    none: '0',
    sm: 'var(--space-4)',
    md: 'var(--space-6)',
    lg: 'var(--space-8)',
  };

  const v = variants[variant];

  const baseStyle = {
    borderRadius: 'var(--radius-lg)',
    transition: 'border-color 150ms cubic-bezier(0.25, 0.46, 0.45, 0.94), box-shadow 150ms cubic-bezier(0.25, 0.46, 0.45, 0.94), background 150ms cubic-bezier(0.25, 0.46, 0.45, 0.94)',
    padding: paddings[padding],
    ...v,
    ...style,
  };

  const Component = onClick ? 'button' : 'div';
  const componentProps = onClick
    ? {
        type: 'button',
        onClick,
        style: {
          ...baseStyle,
          cursor: 'pointer',
          textAlign: 'left',
          width: '100%',
          border: 'none',
          background: 'inherit',
        },
      }
    : { style: baseStyle };

  return (
    <Component
      className={className}
      {...componentProps}
      {...(onClick ? {} : props)}
    >
      {children}
    </Component>
  );
}

export function GlassPanel({
  children,
  heavy = false,
  padding = 'md',
  className = '',
  style = {},
  ...props
}) {
  return (
    <Card
      variant={heavy ? 'glass-heavy' : 'glass'}
      padding={padding}
      className={className}
      style={style}
      {...props}
    >
      {children}
    </Card>
  );
}