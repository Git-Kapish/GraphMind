import React from 'react';
import { CitationBadge } from './ui/Badge';

/**
 * Custom components for react-markdown to render citations, code blocks, etc.
 * with Apple-styled components
 */

export const markdownComponents = {
  // Inline code
  code: ({ children, ...props }) => (
    <code
      {...props}
      style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '0.875em',
        background: 'var(--bg-tertiary)',
        padding: '2px 6px',
        borderRadius: 'var(--radius-sm)',
        color: 'var(--accent-pink)',
        fontWeight: 500,
      }}
    >
      {children}
    </code>
  ),

  // Code blocks
  pre: ({ children, ...props }) => (
    <pre
      {...props}
      style={{
        background: 'var(--bg-tertiary)',
        border: '1px solid var(--glass-border)',
        borderRadius: 'var(--radius-lg)',
        padding: 'var(--space-4)',
        overflow: 'auto',
        fontSize: 'var(--text-sm)',
        lineHeight: 'var(--leading-normal)',
        margin: 'var(--space-4) 0',
      }}
    >
      {React.isValidElement(children) ? (
        <code style={{ color: 'var(--fg-primary)', fontFamily: 'var(--font-mono)' }}>{children.props.children}</code>
      ) : (
        children
      )}
    </pre>
  ),

  // Paragraphs
  p: ({ children, ...props }) => (
    <p
      {...props}
      style={{
        lineHeight: 'var(--leading-relaxed)',
        margin: '0 0 var(--space-3)',
        color: 'var(--fg-primary)',
      }}
    >
      {children}
    </p>
  ),

  // Strong/bold
  strong: ({ children, ...props }) => (
    <strong {...props} style={{ fontWeight: 600, color: 'var(--fg-primary)' }}>
      {children}
    </strong>
  ),

  // Emphasis/italic
  em: ({ children, ...props }) => (
    <em {...props} style={{ fontStyle: 'italic', color: 'var(--fg-primary)' }}>
      {children}
    </em>
  ),

  // Links
  a: ({ href, children, ...props }) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      {...props}
      style={{
        color: 'var(--accent-blue)',
        textDecoration: 'none',
        borderBottom: '1px solid transparent',
        transition: 'border-color 150ms cubic-bezier(0.25, 0.46, 0.45, 0.94)',
        ...props.style,
      }}
      onMouseEnter={(e) => { e.currentTarget.style.borderBottomColor = 'var(--accent-blue)'; }}
      onMouseLeave={(e) => { e.currentTarget.style.borderBottomColor = 'transparent'; }}
    >
      {children}
    </a>
  ),

  // Lists
  ul: ({ children, ...props }) => (
    <ul
      {...props}
      style={{
        margin: 'var(--space-3) 0',
        paddingLeft: 'var(--space-6)',
        lineHeight: 'var(--leading-relaxed)',
      }}
    >
      {children}
    </ul>
  ),

  ol: ({ children, ...props }) => (
    <ol
      {...props}
      style={{
        margin: 'var(--space-3) 0',
        paddingLeft: 'var(--space-6)',
        lineHeight: 'var(--leading-relaxed)',
      }}
    >
      {children}
    </ol>
  ),

  li: ({ children, ...props }) => (
    <li {...props} style={{ margin: 'var(--space-1) 0' }}>{children}</li>
  ),

  // Blockquotes
  blockquote: ({ children, ...props }) => (
    <blockquote
      {...props}
      style={{
        margin: 'var(--space-4) 0',
        padding: 'var(--space-3) var(--space-4)',
        borderLeft: '3px solid var(--accent-blue)',
        background: 'var(--accent-blue-weak)',
        borderRadius: '0 var(--radius-md) var(--radius-md) 0',
        color: 'var(--fg-secondary)',
        fontStyle: 'italic',
      }}
    >
      {children}
    </blockquote>
  ),

  // Headings
  h1: ({ children, ...props }) => (
    <h1 {...props} style={{ fontSize: 'var(--text-2xl)', margin: 'var(--space-6) 0 var(--space-3)', fontWeight: 600 }}>{children}</h1>
  ),
  h2: ({ children, ...props }) => (
    <h2 {...props} style={{ fontSize: 'var(--text-xl)', margin: 'var(--space-5) 0 var(--space-3)', fontWeight: 600 }}>{children}</h2>
  ),
  h3: ({ children, ...props }) => (
    <h3 {...props} style={{ fontSize: 'var(--text-lg)', margin: 'var(--space-4) 0 var(--space-2)', fontWeight: 600 }}>{children}</h3>
  ),

  // Horizontal rule
  hr: ({ ...props }) => (
    <hr {...props} style={{ border: 'none', borderTop: '1px solid var(--glass-border)', margin: 'var(--space-6) 0' }} />
  ),
};

/**
 * Parse answer text and convert [G1], [P2] citations to CitationBadge components
 * This is used as a pre-processor before react-markdown
 */
export function parseCitations(text, onSelectCitation) {
  if (!text) return [];

  // Split by citation patterns [G1], [P2], etc.
  const parts = text.split(/(\[[GP]\d+\])/g);

  return parts.map((part, index) => {
    const match = part.match(/^\[([GP])(\d+)\]$/);
    if (match) {
      const isGraph = match[1] === 'G';
      return (
        <CitationBadge
          key={index}
          sourceType={isGraph ? 'graph' : 'vector'}
          onClick={() => onSelectCitation({ label: part, source_type: isGraph ? 'graph' : 'vector' })}
        >
          {part}
        </CitationBadge>
      );
    }
    return <span key={index}>{part}</span>;
  });
}