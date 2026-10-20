import React, { forwardRef } from 'react';

const Input = forwardRef(function Input({
  type = 'text',
  value,
  onChange,
  onBlur,
  onFocus,
  placeholder,
  disabled = false,
  error = false,
  className = '',
  style = {},
  'aria-label': ariaLabel,
  'aria-describedby': ariaDescribedBy,
  id,
  ...props
}, ref) {
  const inputStyles = {
    width: '100%',
    background: 'var(--bg-secondary)',
    border: `1px solid ${error ? 'var(--accent-red)' : 'var(--glass-border)'}`,
    borderRadius: 'var(--radius-md)',
    color: 'var(--fg-primary)',
    fontFamily: 'var(--font-system)',
    fontSize: 'var(--text-base)',
    lineHeight: 'var(--leading-normal)',
    padding: 'var(--space-3) var(--space-4)',
    transition: 'all 150ms cubic-bezier(0.25, 0.46, 0.45, 0.94)',
    resize: 'none',
    outline: 'none',
    boxSizing: 'border-box',
    ...style,
  };

  const focusStyles = {
    borderColor: error ? 'var(--accent-red)' : 'var(--accent-blue)',
    boxShadow: error
      ? '0 0 0 3px var(--accent-red-weak)'
      : '0 0 0 3px var(--accent-blue-weak)',
    background: 'var(--bg-primary)',
  };

  return (
    <div className={className}>
      <input
        ref={ref}
        type={type}
        value={value}
        onChange={onChange}
        onBlur={onBlur}
        onFocus={onFocus}
        placeholder={placeholder}
        disabled={disabled}
        aria-label={ariaLabel}
        aria-describedby={ariaDescribedBy}
        aria-invalid={error}
        id={id}
        style={inputStyles}
        {...props}
      />
    </div>
  );
});

Input.displayName = 'Input';

const Textarea = forwardRef(function Textarea({
  value,
  onChange,
  onBlur,
  onFocus,
  placeholder,
  disabled = false,
  error = false,
  className = '',
  style = {},
  'aria-label': ariaLabel,
  'aria-describedby': ariaDescribedBy,
  id,
  rows = 1,
  minHeight = '44px',
  maxHeight = '200px',
  ...props
}, ref) {
  const textareaStyles = {
    width: '100%',
    background: 'var(--bg-secondary)',
    border: `1px solid ${error ? 'var(--accent-red)' : 'var(--glass-border)'}`,
    borderRadius: 'var(--radius-md)',
    color: 'var(--fg-primary)',
    fontFamily: 'var(--font-system)',
    fontSize: 'var(--text-base)',
    lineHeight: 'var(--leading-normal)',
    padding: 'var(--space-3) var(--space-4)',
    transition: 'all 150ms cubic-bezier(0.25, 0.46, 0.45, 0.94)',
    resize: 'none',
    outline: 'none',
    boxSizing: 'border-box',
    minHeight,
    maxHeight,
    overflow: 'hidden',
    ...style,
  };

  return (
    <div className={className}>
      <textarea
        ref={ref}
        value={value}
        onChange={onChange}
        onBlur={onBlur}
        onFocus={onFocus}
        placeholder={placeholder}
        disabled={disabled}
        aria-label={ariaLabel}
        aria-describedby={ariaDescribedBy}
        aria-invalid={error}
        id={id}
        rows={rows}
        style={textareaStyles}
        {...props}
      />
    </div>
  );
});

Textarea.displayName = 'Textarea';

export { Input, Textarea };