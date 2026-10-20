import React, { useRef, useEffect, useState, useCallback } from 'react';
import { motion, animate } from 'framer-motion';
import { Send, Mic, Paperclip, Command } from 'lucide-react';
import { SegmentedControl } from './ui/SegmentedControl';
import { Textarea } from './ui/Input';
import { Button } from './ui/Button';

const MODE_OPTIONS = [
  { value: 'auto', label: 'Auto', title: 'Auto-Routed Hybrid (recommended)' },
  { value: 'compare', label: 'Compare', title: 'Side-by-Side: Vector vs Hybrid' },
  { value: 'vector', label: 'Vector', title: 'Dense Vector Baseline Only' },
  { value: 'graph', label: 'Graph', title: 'Knowledge Graph Only' },
  { value: 'hybrid', label: 'Hybrid', title: 'Forced Hybrid (Graph + Vector)' },
];

const springConfig = { type: 'spring', stiffness: 300, damping: 30, mass: 1 };

export function InputBar({
  mode,
  setMode,
  inputValue,
  setInputValue,
  onSubmit,
  isLoading = false,
  disabled = false,
  inputRef,
}) {
  const textareaRef = useRef(null);
  const [inputHeight, setInputHeight] = useState(56);
  const isComposing = useRef(false);

  // Auto-resize textarea
  const handleInputChange = useCallback((e) => {
    const value = e.target.value;
    setInputValue(value);

    // Auto-resize
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      const newHeight = Math.min(textareaRef.current.scrollHeight, 200);
      setInputHeight(newHeight);
      textareaRef.current.style.height = `${newHeight}px`;
    }
  }, [setInputValue]);

  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Enter' && !e.shiftKey && !isComposing.current) {
      e.preventDefault();
      handleSubmit();
    }
  }, []);

  const handleCompositionStart = useCallback(() => {
    isComposing.current = true;
  }, []);

  const handleCompositionEnd = useCallback((e) => {
    isComposing.current = false;
    if (e.nativeEvent.data) {
      handleInputChange({ target: { value: e.target.value } });
    }
  }, [handleInputChange]);

  const handleSubmit = useCallback(() => {
    if (!inputValue.trim() || isLoading || disabled) return;
    onSubmit(inputValue.trim(), mode);
  }, [inputValue, mode, isLoading, disabled, onSubmit]);

  // Sync external inputRef
  useEffect(() => {
    if (inputRef) {
      inputRef.current = textareaRef.current;
    }
  }, [inputRef]);

  return (
    <motion.form
      onSubmit={(e) => { e.preventDefault(); handleSubmit(); }}
      className="input-bar"
      style={{
        position: 'sticky',
        bottom: 0,
        zIndex: 50,
        background: 'linear-gradient(to top, var(--bg-primary) 60%, transparent)',
        padding: 'var(--space-4) var(--space-6)',
        borderTop: '1px solid var(--glass-border)',
      }}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={springConfig}
    >
      <div style={{ display: 'flex', gap: 'var(--space-3)', alignItems: 'flex-end', maxWidth: 'var(--chat-max-width)', margin: '0 auto' }}>
        {/* Compact Mode Selector */}
        <div style={{ flexShrink: 0 }}>
          <SegmentedControl
            options={MODE_OPTIONS}
            value={mode}
            onChange={setMode}
            size="sm"
            aria-label="Retrieval mode"
            disabled={isLoading || disabled}
          />
        </div>

        {/* Textarea */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <Textarea
            ref={textareaRef}
            value={inputValue}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            onCompositionStart={handleCompositionStart}
            onCompositionEnd={handleCompositionEnd}
            onBlur={() => {}}
            onFocus={() => {}}
            placeholder="Message GraphMind..."
            disabled={isLoading || disabled}
            style={{
              minHeight: `${inputHeight}px`,
              maxHeight: '200px',
              fontSize: 'var(--text-base)',
              padding: 'var(--space-3) var(--space-4)',
              borderRadius: 'var(--radius-lg)',
              border: `1px solid ${isLoading ? 'var(--accent-blue)' : 'var(--glass-border)'}`,
              boxShadow: isLoading ? '0 0 0 3px var(--accent-blue-weak)' : 'none',
              transition: 'all 150ms cubic-bezier(0.25, 0.46, 0.45, 0.94)',
            }}
            aria-label="Enter your question"
          />
        </div>

        {/* Action Buttons */}
        <div style={{ display: 'flex', gap: 'var(--space-2)', flexShrink: 0 }}>
          <Button
            variant="ghost"
            size="sm"
            disabled={isLoading || disabled}
            aria-label="Attach file"
            title="Attach file"
          >
            <Paperclip size={16} />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            disabled={isLoading || disabled}
            aria-label="Voice input"
            title="Voice input"
          >
            <Mic size={16} />
          </Button>
          <Button
            type="submit"
            variant="primary"
            size="md"
            disabled={!inputValue.trim() || isLoading || disabled}
            rightIcon={<Send size={18} />}
            aria-label="Send query"
            style={{
              height: '44px',
              borderRadius: 'var(--radius-lg)',
            }}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          />
        </div>
      </div>

      {/* Keyboard hint */}
      <div style={{
        display: 'flex',
        justifyContent: 'flex-end',
        marginTop: 'var(--space-2)',
        paddingRight: 'var(--space-6)',
      }}>
        <kbd style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '4px',
          padding: '2px 8px',
          fontSize: 'var(--text-xs)',
          fontFamily: 'var(--font-mono)',
          color: 'var(--fg-tertiary)',
          background: 'var(--bg-tertiary)',
          border: '1px solid var(--glass-border)',
          borderRadius: 'var(--radius-sm)',
        }}>
          <span style={{ fontWeight: 600 }}>⌘</span>
          <span>Enter</span>
          <span style={{ color: 'var(--fg-quaternary)' }}>to send</span>
        </kbd>
      </div>
    </motion.form>
  );
}