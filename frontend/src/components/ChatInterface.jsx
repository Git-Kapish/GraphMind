import React, { useState, useRef, useEffect, useCallback, useImperativeHandle } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { EmptyState } from './EmptyState';
import { InputBar } from './InputBar';
import { MessageBubble } from './MessageBubble';

// Simple scroll area implementation
function ScrollArea({ children, ref, className = '', style = {}, onScroll }) {
  const scrollRef = useRef(null);

  useImperativeHandle(ref, () => ({
    scrollToBottom: (behavior = 'smooth') => {
      if (scrollRef.current) {
        scrollRef.current.scrollTo({ top: scrollRef.current.scrollHeight, behavior });
      }
    },
    scrollToTop: (behavior = 'smooth') => {
      if (scrollRef.current) {
        scrollRef.current.scrollTo({ top: 0, behavior });
      }
    },
  }));

  return (
    <div
      ref={scrollRef}
      className={className}
      style={{
        overflowY: 'auto',
        overflowX: 'hidden',
        ...style,
      }}
      onScroll={onScroll}
    >
      {children}
    </div>
  );
}

const springConfig = { type: 'spring', stiffness: 300, damping: 30, mass: 1 };

export default function ChatInterface({
  messages,
  mode,
  setMode,
  onSearch,
  onSelectCitation,
  messagesEndRef,
  chatContainerRef,
}) {
  const [inputValue, setInputValue] = useState('');
  const textareaRef = useRef(null);
  const scrollAreaRef = useRef(null);
  const isComposing = useRef(false);
  const hasMessages = messages.length > 0;

  // Auto-scroll to bottom when messages change
  const scrollToBottom = useCallback(() => {
    if (scrollAreaRef.current) {
      const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      scrollAreaRef.current.scrollToBottom(prefersReducedMotion ? 'auto' : 'smooth');
    }
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // Handle submit from InputBar
  const handleSubmit = useCallback((query, currentMode) => {
    setInputValue('');
    onSearch(query, currentMode);
  }, [onSearch]);

  // Handle quick prompt selection
  const handleQuickPrompt = useCallback((question) => {
    setInputValue(question);
    // Trigger auto-resize via InputBar's internal logic
    setTimeout(() => {
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
        const newHeight = Math.min(textareaRef.current.scrollHeight, 200);
        textareaRef.current.style.height = `${newHeight}px`;
      }
    }, 0);
    onSearch(question, mode);
  }, [mode, onSearch]);

  return (
    <div
      ref={chatContainerRef}
      className="chat-page"
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100vh',
        minHeight: '100vh',
        background: 'var(--bg-primary)',
      }}
    >
      {/* Main Chat Area */}
      <main
        className="main-content"
        style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          paddingTop: 'var(--topbar-height)',
          overflow: 'hidden',
        }}
      >
        <ScrollArea
          ref={scrollAreaRef}
          style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            padding: 'var(--space-6) var(--space-4)',
            maxWidth: 'var(--chat-max-width)',
            width: '100%',
            margin: '0 auto',
          }}
        >
          {!hasMessages ? (
            <EmptyState
              mode={mode}
              setMode={setMode}
              inputValue={inputValue}
              setInputValue={setInputValue}
              onSubmit={handleSubmit}
              inputRef={textareaRef}
            />
          ) : (
            <>
              {/* Message List */}
              <div
                className="message-list"
                role="list"
                aria-label="Conversation history"
                style={{
                  flex: 1,
                  display: 'flex',
                  flexDirection: 'column',
                  width: '100%',
                }}
              >
                <AnimatePresence mode="popLayout">
                  {messages.map((message, idx) => (
                    <MessageBubble
                      key={`${message.id || idx}-${message.timestamp}`}
                      message={message}
                      onSelectCitation={onSelectCitation}
                      isLast={idx === messages.length - 1}
                    />
                  ))}
                </AnimatePresence>
                <div ref={messagesEndRef} style={{ height: 'var(--space-4)' }} />
              </div>
            </>
          )}
        </ScrollArea>

        {/* Input Bar */}
        <InputBar
          mode={mode}
          setMode={setMode}
          inputValue={inputValue}
          setInputValue={setInputValue}
          onSubmit={handleSubmit}
          isLoading={messages.some(m => m.loading)}
          inputRef={textareaRef}
        />
      </main>
    </div>
  );
}