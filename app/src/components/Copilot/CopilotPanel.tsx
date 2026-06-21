import { useState, useRef, useEffect, memo, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X, Send, Sparkles, ChevronDown, ChevronUp, Database,
  AlertCircle, Bot, User, RotateCcw, Zap, Maximize2, Minimize2,
  Copy, Check,
} from 'lucide-react';
import { useCopilot, type CopilotMessage } from '@/hooks/useCopilot';
import type { CopilotResponse } from '@/api/copilot';

// ---------------------------------------------------------------------------
// Suggestion chips
// ---------------------------------------------------------------------------
const SUGGESTION_CHIPS = [
  "What's the overall health of our vendor portfolio?",
  'List all breach alerts in the last 48 hours',
  'Which vendors have critical alerts?',
  'Show vendors with expiring certifications',
  'Who are our top 5 highest-risk vendors?',
  'Which vendors are overdue for assessment?',
];

// ---------------------------------------------------------------------------
// Custom markdown components — critical for proper table rendering
// ---------------------------------------------------------------------------
function MarkdownTable({ children }: { children: React.ReactNode }) {
  return (
    <div className="copilot-table-wrapper">
      <table>{children}</table>
    </div>
  );
}

const markdownComponents = {
  table: ({ children }: any) => <MarkdownTable>{children}</MarkdownTable>,
  thead: ({ children }: any) => <thead>{children}</thead>,
  tbody: ({ children }: any) => <tbody>{children}</tbody>,
  tr: ({ children }: any) => <tr>{children}</tr>,
  th: ({ children }: any) => <th>{children}</th>,
  td: ({ children }: any) => <td>{children}</td>,
  code: ({ inline, children, ...props }: any) =>
    inline ? (
      <code className="copilot-inline-code" {...props}>{children}</code>
    ) : (
      <div className="copilot-code-block">
        <pre {...props}><code>{children}</code></pre>
      </div>
    ),
  p: ({ children }: any) => <p className="copilot-p">{children}</p>,
  ul: ({ children }: any) => <ul className="copilot-ul">{children}</ul>,
  ol: ({ children }: any) => <ol className="copilot-ol">{children}</ol>,
  li: ({ children }: any) => <li className="copilot-li">{children}</li>,
  h1: ({ children }: any) => <h2 className="copilot-h2">{children}</h2>,
  h2: ({ children }: any) => <h2 className="copilot-h2">{children}</h2>,
  h3: ({ children }: any) => <h3 className="copilot-h3">{children}</h3>,
  strong: ({ children }: any) => <strong className="copilot-strong">{children}</strong>,
  blockquote: ({ children }: any) => <blockquote className="copilot-blockquote">{children}</blockquote>,
};

// ---------------------------------------------------------------------------
// Copy button
// ---------------------------------------------------------------------------
function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button
      onClick={handleCopy}
      title="Copy answer"
      className="flex items-center gap-1 rounded px-2 py-0.5 text-[10px] text-sg-text-secondary transition-colors hover:bg-sg-surface-muted hover:text-sg-text-primary"
    >
      {copied ? <Check className="h-3 w-3 text-green-500" /> : <Copy className="h-3 w-3" />}
      {copied ? 'Copied' : 'Copy'}
    </button>
  );
}

// ---------------------------------------------------------------------------
// Provenance footer
// ---------------------------------------------------------------------------
function ProvenanceFooter({ dataUsed }: { dataUsed: CopilotResponse['data_used'] }) {
  const [expanded, setExpanded] = useState(false);
  if (!dataUsed || dataUsed.length === 0) return null;

  return (
    <div className="mt-3 rounded-lg border border-sg-border-subtle bg-sg-surface-muted/60 px-3 py-2 text-xs">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-1.5 text-sg-text-secondary hover:text-sg-text-primary transition-colors"
      >
        <Database className="h-3 w-3 flex-shrink-0 text-violet-400" />
        <span className="font-semibold text-violet-400">Data sources</span>
        <span className="ml-1 rounded-full bg-violet-500/15 px-1.5 py-0.5 text-[9px] font-bold text-violet-400">
          {dataUsed.length}
        </span>
        <span className="ml-auto">
          {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
        </span>
      </button>
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="overflow-hidden"
          >
            <ul className="mt-2 space-y-1.5">
              {dataUsed.map((src, i) => (
                <li key={i} className="flex items-start gap-2 text-sg-text-secondary">
                  <span className="mt-1.5 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-violet-400" />
                  <div className="min-w-0">
                    <code className="font-mono text-violet-400">{src.endpoint}</code>
                    {src.summary && (
                      <span className="ml-1 text-sg-text-secondary opacity-70">→ {src.summary}</span>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Follow-up chips
// ---------------------------------------------------------------------------
function FollowUpChips({
  suggestions,
  onSelect,
  disabled,
}: {
  suggestions: string[];
  onSelect: (s: string) => void;
  disabled: boolean;
}) {
  if (!suggestions || suggestions.length === 0) return null;
  return (
    <div className="mt-3">
      <p className="mb-1.5 text-[9px] font-semibold uppercase tracking-wider text-sg-text-secondary">
        Follow-up suggestions
      </p>
      <div className="flex flex-wrap gap-1.5">
        {suggestions.map((s, i) => (
          <button
            key={i}
            onClick={() => onSelect(s)}
            disabled={disabled}
            className="rounded-full border border-violet-500/20 bg-violet-500/5 px-3 py-1 text-xs text-violet-400 transition-all hover:border-violet-500/50 hover:bg-violet-500/10 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Confidence badge
// ---------------------------------------------------------------------------
function ConfidenceBadge({ confidence }: { confidence: string }) {
  const map: Record<string, { label: string; cls: string; dot: string }> = {
    high:    { label: 'Live data',    cls: 'text-emerald-500 bg-emerald-500/10 border-emerald-500/20', dot: 'bg-emerald-500' },
    partial: { label: 'Partial data', cls: 'text-amber-500 bg-amber-500/10 border-amber-500/20',       dot: 'bg-amber-500'   },
    none:    { label: 'No data',      cls: 'text-red-500 bg-red-500/10 border-red-500/20',              dot: 'bg-red-500'     },
  };
  const { label, cls, dot } = map[confidence] || map.none;
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-semibold ${cls}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${dot}`} />
      {label}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Single message bubble
// ---------------------------------------------------------------------------
const MessageBubble = memo(function MessageBubble({
  msg,
  onFollowUp,
  isLastAssistant,
  isLoading,
  isExpanded,
}: {
  msg: CopilotMessage;
  onFollowUp: (s: string) => void;
  isLastAssistant: boolean;
  isLoading: boolean;
  isExpanded: boolean;
}) {
  const isUser = msg.role === 'user';

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2, ease: 'easeOut' }}
      className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
    >
      {/* Avatar */}
      <div
        className={`flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full text-xs font-bold ${
          isUser
            ? 'bg-sg-primary text-white'
            : 'border border-violet-500/30 bg-gradient-to-br from-violet-600/20 to-indigo-600/20'
        }`}
      >
        {isUser ? <User className="h-3.5 w-3.5" /> : <Bot className="h-3.5 w-3.5 text-violet-400" />}
      </div>

      {/* Content */}
      <div className={`min-w-0 flex-1 ${isUser ? 'flex flex-col items-end' : ''}`}>
        {/* User message */}
        {isUser && (
          <div className="inline-block max-w-[85%] rounded-2xl rounded-tr-sm bg-sg-primary px-4 py-2.5 text-sm text-white">
            {msg.content}
          </div>
        )}

        {/* Loading shimmer */}
        {!isUser && msg.isLoading && (
          <div className="flex items-center gap-3 rounded-2xl rounded-tl-sm border border-sg-border-subtle bg-sg-surface px-4 py-3">
            <div className="flex gap-1">
              {[0, 1, 2].map((i) => (
                <div
                  key={i}
                  className="h-1.5 w-1.5 rounded-full bg-violet-400 animate-bounce"
                  style={{ animationDelay: `${i * 0.15}s` }}
                />
              ))}
            </div>
            <span className="text-xs text-sg-text-secondary">Querying live data…</span>
          </div>
        )}

        {/* Error state */}
        {!isUser && msg.error && (
          <div className="flex items-start gap-2 rounded-2xl rounded-tl-sm border border-red-500/20 bg-red-500/5 px-4 py-3 text-sm text-red-500">
            <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
            <span>{msg.error}</span>
          </div>
        )}

        {/* Assistant answer */}
        {!isUser && !msg.isLoading && !msg.error && msg.content && (
          <div className="w-full rounded-2xl rounded-tl-sm border border-sg-border-subtle bg-sg-surface">
            {/* Answer header bar */}
            <div className="flex items-center justify-between border-b border-sg-border-subtle/60 px-4 py-2">
              <div className="flex items-center gap-2">
                <Zap className="h-3 w-3 text-violet-400" />
                {msg.response && <ConfidenceBadge confidence={msg.response.confidence} />}
              </div>
              <CopyButton text={msg.content} />
            </div>

            {/* Scrollable markdown area */}
            <div className={`px-4 py-3 ${isExpanded ? '' : 'max-h-[520px] overflow-y-auto'} copilot-scroll`}>
              <div className="copilot-markdown">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={markdownComponents}
                >
                  {msg.content}
                </ReactMarkdown>
              </div>
            </div>

            {/* Footer: provenance + follow-ups */}
            {(msg.response?.data_used?.length || (isLastAssistant && msg.response?.follow_up_suggestions?.length)) ? (
              <div className="border-t border-sg-border-subtle/60 px-4 pb-3 pt-2">
                {msg.response?.data_used && msg.response.data_used.length > 0 && (
                  <ProvenanceFooter dataUsed={msg.response.data_used} />
                )}
                {isLastAssistant && msg.response?.follow_up_suggestions && (
                  <FollowUpChips
                    suggestions={msg.response.follow_up_suggestions}
                    onSelect={onFollowUp}
                    disabled={isLoading}
                  />
                )}
              </div>
            ) : null}
          </div>
        )}
      </div>
    </motion.div>
  );
});

// ---------------------------------------------------------------------------
// Empty state
// ---------------------------------------------------------------------------
function EmptyState({ onSelect }: { onSelect: (s: string) => void }) {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-10 text-center">
      <div className="mb-5 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-600/25 to-indigo-600/25 ring-1 ring-violet-500/25 shadow-lg">
        <Sparkles className="h-8 w-8 text-violet-400" />
      </div>
      <h3 className="text-base font-bold text-sg-text-primary">VendorSentry Copilot</h3>
      <p className="mt-1.5 max-w-xs text-sm leading-relaxed text-sg-text-secondary">
        Ask anything about your vendor risk portfolio. Every answer is grounded in live data — never guessed.
      </p>

      <div className="mt-7 w-full">
        <p className="mb-2 text-left text-[10px] font-bold uppercase tracking-widest text-sg-text-secondary">
          Try asking…
        </p>
        <div className="space-y-1.5">
          {SUGGESTION_CHIPS.map((s) => (
            <button
              key={s}
              onClick={() => onSelect(s)}
              className="group flex w-full items-center gap-2.5 rounded-xl border border-sg-border-subtle bg-sg-surface px-3.5 py-2.5 text-left text-xs text-sg-text-secondary transition-all hover:border-violet-500/40 hover:bg-violet-500/5 hover:text-sg-text-primary"
            >
              <Sparkles className="h-3 w-3 flex-shrink-0 text-violet-400 opacity-0 transition-opacity group-hover:opacity-100" />
              {s}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main CopilotPanel
// ---------------------------------------------------------------------------
interface CopilotPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

const PANEL_WIDTH_NORMAL  = 520;
const PANEL_WIDTH_WIDE    = 760;

export default function CopilotPanel({ isOpen, onClose }: CopilotPanelProps) {
  const [inputValue, setInputValue]   = useState('');
  const [isExpanded, setIsExpanded]   = useState(false);      // fullscreen toggle
  const [panelWidth, setPanelWidth]   = useState(PANEL_WIDTH_NORMAL);
  const [isDragging, setIsDragging]   = useState(false);
  const dragStartX   = useRef(0);
  const dragStartW   = useRef(PANEL_WIDTH_NORMAL);

  const { messages, isLoading, sendQuery, sendFollowUp, clearMessages } = useCopilot();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef       = useRef<HTMLTextAreaElement>(null);

  // Scroll to bottom on new message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Focus input when opened
  useEffect(() => {
    if (isOpen) setTimeout(() => inputRef.current?.focus(), 300);
  }, [isOpen]);

  // Keyboard shortcut: Escape to close
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        if (isExpanded) setIsExpanded(false);
        else onClose();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [isOpen, isExpanded, onClose]);

  // Drag-to-resize handlers
  const onDragStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    dragStartX.current = e.clientX;
    dragStartW.current = panelWidth;
    setIsDragging(true);
  }, [panelWidth]);

  useEffect(() => {
    if (!isDragging) return;
    const onMove = (e: MouseEvent) => {
      const delta = dragStartX.current - e.clientX;
      const newW = Math.min(Math.max(dragStartW.current + delta, 400), 1100);
      setPanelWidth(newW);
    };
    const onUp = () => setIsDragging(false);
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
  }, [isDragging]);

  const handleSubmit = () => {
    const q = inputValue.trim();
    if (!q || isLoading) return;
    setInputValue('');
    sendQuery(q);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  // Auto-grow textarea
  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputValue(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
  };

  const lastAssistantIdx = messages.reduce(
    (acc, msg, i) => (msg.role === 'assistant' ? i : acc),
    -1
  );

  const widthClass   = isExpanded ? 'w-screen' : '';

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          {!isExpanded && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={onClose}
              className="fixed inset-0 z-40 bg-black/25 backdrop-blur-[2px]"
            />
          )}

          {/* Panel */}
          <motion.div
            initial={{ x: '100%', opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: '100%', opacity: 0 }}
            transition={{ type: 'spring', damping: 28, stiffness: 280 }}
            style={{ width: isExpanded ? '100vw' : panelWidth }}
            className={`fixed right-0 top-0 z-50 flex h-full flex-col border-l border-sg-border-subtle bg-sg-surface shadow-2xl ${widthClass}`}
          >
            {/* Drag handle (left edge) */}
            {!isExpanded && (
              <div
                onMouseDown={onDragStart}
                className={`absolute left-0 top-0 h-full w-1 cursor-ew-resize transition-colors ${
                  isDragging
                    ? 'bg-violet-500/60'
                    : 'bg-transparent hover:bg-violet-500/30'
                }`}
                title="Drag to resize"
              />
            )}

            {/* ── Header ── */}
            <div className="flex flex-shrink-0 items-center justify-between border-b border-sg-border-subtle px-5 py-3.5">
              <div className="flex items-center gap-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-br from-violet-600/25 to-indigo-600/25 ring-1 ring-violet-500/25">
                  <Sparkles className="h-4 w-4 text-violet-400" />
                </div>
                <div>
                  <h2 className="text-sm font-bold leading-tight text-sg-text-primary">
                    Copilot
                  </h2>
                  <p className="text-[10px] leading-tight text-sg-text-secondary">
                    Live data · No hallucinations · {isExpanded ? 'Full view' : `${panelWidth}px`}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-1">
                {messages.length > 0 && (
                  <button
                    onClick={clearMessages}
                    title="Clear conversation"
                    className="rounded-lg p-1.5 text-sg-text-secondary transition-colors hover:bg-sg-surface-muted hover:text-sg-text-primary"
                  >
                    <RotateCcw className="h-4 w-4" />
                  </button>
                )}

                {/* Wide preset toggle */}
                {!isExpanded && (
                  <button
                    onClick={() => setPanelWidth(panelWidth === PANEL_WIDTH_NORMAL ? PANEL_WIDTH_WIDE : PANEL_WIDTH_NORMAL)}
                    title={panelWidth === PANEL_WIDTH_WIDE ? 'Compact view' : 'Wide view'}
                    className="rounded-lg p-1.5 text-sg-text-secondary transition-colors hover:bg-sg-surface-muted hover:text-sg-text-primary"
                  >
                    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      {panelWidth === PANEL_WIDTH_WIDE
                        ? <><path d="M8 3H5a2 2 0 0 0-2 2v3"/><path d="M21 8V5a2 2 0 0 0-2-2h-3"/><path d="M3 16v3a2 2 0 0 0 2 2h3"/><path d="M16 21h3a2 2 0 0 0 2-2v-3"/></>
                        : <><path d="M3 8V5a2 2 0 0 1 2-2h3"/><path d="M16 3h3a2 2 0 0 1 2 2v3"/><path d="M21 16v3a2 2 0 0 1-2 2h-3"/><path d="M8 21H5a2 2 0 0 1-2-2v-3"/></>
                      }
                    </svg>
                  </button>
                )}

                {/* Fullscreen toggle */}
                <button
                  onClick={() => setIsExpanded(!isExpanded)}
                  title={isExpanded ? 'Exit fullscreen' : 'Fullscreen'}
                  className="rounded-lg p-1.5 text-sg-text-secondary transition-colors hover:bg-sg-surface-muted hover:text-violet-400"
                >
                  {isExpanded
                    ? <Minimize2 className="h-4 w-4" />
                    : <Maximize2 className="h-4 w-4" />
                  }
                </button>

                <button
                  onClick={onClose}
                  className="rounded-lg p-1.5 text-sg-text-secondary transition-colors hover:bg-sg-surface-muted hover:text-sg-text-primary"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>

            {/* ── Messages area ── */}
            <div className="flex-1 overflow-y-auto copilot-scroll">
              {/* Expanded layout: two columns when wide enough */}
              <div className={`mx-auto w-full px-5 py-5 ${isExpanded ? 'max-w-5xl' : ''}`}>
                {messages.length === 0 ? (
                  <EmptyState
                    onSelect={(s) => {
                      setInputValue('');
                      sendQuery(s);
                    }}
                  />
                ) : (
                  <div className="space-y-6">
                    {messages.map((msg, i) => (
                      <MessageBubble
                        key={msg.id}
                        msg={msg}
                        onFollowUp={sendFollowUp}
                        isLastAssistant={i === lastAssistantIdx}
                        isLoading={isLoading}
                        isExpanded={isExpanded}
                      />
                    ))}
                    <div ref={messagesEndRef} />
                  </div>
                )}
              </div>
            </div>

            {/* ── Input area ── */}
            <div className="flex-shrink-0 border-t border-sg-border-subtle bg-sg-surface p-4">
              <div className={`mx-auto w-full ${isExpanded ? 'max-w-3xl' : ''}`}>
                <div className="flex items-end gap-2 rounded-xl border border-sg-border-subtle bg-sg-surface-muted px-3 py-2 transition-all focus-within:border-violet-500/50 focus-within:ring-2 focus-within:ring-violet-500/10">
                  <textarea
                    ref={inputRef}
                    value={inputValue}
                    onChange={handleInput}
                    onKeyDown={handleKeyDown}
                    placeholder="Ask anything about your vendor risk portfolio… (Enter to send, Shift+Enter for newline)"
                    rows={1}
                    style={{ resize: 'none', minHeight: '36px', maxHeight: '120px' }}
                    className="flex-1 bg-transparent py-1 text-sm text-sg-text-primary placeholder-sg-text-secondary outline-none"
                    disabled={isLoading}
                  />
                  <button
                    onClick={handleSubmit}
                    disabled={!inputValue.trim() || isLoading}
                    className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-violet-600 to-indigo-600 text-white shadow-sm transition-all hover:from-violet-500 hover:to-indigo-500 hover:shadow-md disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    {isLoading
                      ? <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                      : <Send className="h-3.5 w-3.5" />
                    }
                  </button>
                </div>
                <div className="mt-2 flex items-center justify-between px-1">
                  <p className="text-[10px] text-sg-text-secondary">
                    All answers grounded in live VendorSentry data
                  </p>
                  <p className="text-[10px] text-sg-text-secondary">
                    {messages.filter(m => m.role === 'user').length} queries this session
                  </p>
                </div>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
