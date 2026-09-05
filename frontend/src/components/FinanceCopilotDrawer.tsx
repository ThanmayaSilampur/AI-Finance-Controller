import React, { useState, useRef, useEffect } from 'react';
import {
  BrainCircuit,
  X,
  Send,
  Loader2,
  Sparkles,
  AlertTriangle,
  RotateCcw,
  Scale,
  Search,
  CheckCircle2,
} from 'lucide-react';
import { api, ApiError } from '../api/client';
import { CopilotChatMessage, CopilotQueryResponse } from '../api/types';

interface MessageItem {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  referencedTransactions?: string[];
  referencedExceptions?: string[];
  timestamp: string;
}

interface FinanceCopilotDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  activeBatchId?: string | null;
  onSelectTransaction?: (transactionId: string) => void;
}

const QUICK_SUGGESTIONS = [
  {
    icon: Scale,
    title: 'Batch Discrepancies',
    prompt: 'Summarize the overall match rate, total variance, and primary exceptions in this batch.',
  },
  {
    icon: AlertTriangle,
    title: 'Pending Reviews',
    prompt: 'Which exceptions are currently pending review, and what are their recommended actions?',
  },
  {
    icon: Search,
    title: 'Amount Variances',
    prompt: 'Explain the amount mismatch discrepancies between Payment Gateway and Bank Settlement.',
  },
  {
    icon: CheckCircle2,
    title: 'Audit & Governance',
    prompt: 'What is the current review status distribution and audit history for this run?',
  },
];

export const FinanceCopilotDrawer: React.FC<FinanceCopilotDrawerProps> = ({
  isOpen,
  onClose,
  activeBatchId,
  onSelectTransaction,
}) => {
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const chatBottomRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (isOpen) {
      scrollToBottom();
    }
  }, [messages, isOpen]);

  if (!isOpen) return null;

  const handleSend = async (queryToSend?: string) => {
    const query = (queryToSend || inputText).trim();
    if (!query || isLoading) return;

    setError(null);
    setInputText('');

    const userMessage: MessageItem = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: query,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    // Prepare conversation history
    const history: CopilotChatMessage[] = messages.slice(-6).map((m) => ({
      role: m.role,
      content: m.content,
    }));

    try {
      const res: CopilotQueryResponse = await api.queryCopilot({
        query,
        batch_id: activeBatchId || undefined,
        history,
      });

      const assistantMessage: MessageItem = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: res.answer,
        referencedTransactions: res.referenced_transactions,
        referencedExceptions: res.referenced_exceptions,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err: any) {
      let errMsg = 'Failed to get answer from AI Copilot.';
      if (err instanceof ApiError) {
        errMsg = err.message;
      } else if (err.message) {
        errMsg = err.message;
      }
      setError(errMsg);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const renderFormattedContent = (content: string) => {
    // Simple line-based markdown renderer
    return content.split('\n').map((line, idx) => {
      if (line.startsWith('### ')) {
        return (
          <h4 key={idx} className="text-xs font-bold text-white uppercase tracking-wider mt-2 mb-1">
            {line.replace('### ', '')}
          </h4>
        );
      }
      if (line.startsWith('## ')) {
        return (
          <h3 key={idx} className="text-sm font-bold text-white mt-3 mb-1.5">
            {line.replace('## ', '')}
          </h3>
        );
      }
      if (line.startsWith('* ') || line.startsWith('- ')) {
        return (
          <li key={idx} className="ml-4 list-disc text-slate-200 text-xs py-0.5">
            <span dangerouslySetInnerHTML={{ __html: formatInlineMarkdown(line.slice(2)) }} />
          </li>
        );
      }
      if (!line.trim()) {
        return <div key={idx} className="h-1.5" />;
      }
      return (
        <p key={idx} className="text-xs text-slate-200 leading-relaxed mb-1">
          <span dangerouslySetInnerHTML={{ __html: formatInlineMarkdown(line) }} />
        </p>
      );
    });
  };

  const formatInlineMarkdown = (text: string): string => {
    return text
      .replace(/\*\*(.*?)\*\*/g, '<strong class="font-bold text-white">$1</strong>')
      .replace(/\*(.*?)\*/g, '<em class="italic text-slate-300">$1</em>')
      .replace(/`([^`]+)`/g, '<code class="px-1 py-0.5 rounded bg-slate-950 text-blue-300 font-mono text-[11px] border border-slate-800">$1</code>');
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-black/60 backdrop-blur-xs flex justify-end animate-in fade-in duration-200">
      <div className="w-full max-w-xl bg-slate-950 border-l border-slate-800 shadow-2xl flex flex-col h-full">
        {/* Drawer Header */}
        <div className="px-6 py-4 bg-slate-900 border-b border-slate-800 flex items-center justify-between sticky top-0 z-10">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-purple-600/20 text-purple-400 border border-purple-500/30">
              <BrainCircuit className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-bold text-white tracking-wide">
                  Finance Controller Copilot
                </h2>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-purple-950 text-purple-300 border border-purple-800">
                  AI Assistant
                </span>
              </div>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Grounded strictly in active reconciliation records & telemetry
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {messages.length > 0 && (
              <button
                onClick={() => setMessages([])}
                className="p-1.5 text-slate-400 hover:text-white rounded hover:bg-slate-800 transition"
                title="Clear conversation"
              >
                <RotateCcw className="w-4 h-4" />
              </button>
            )}
            <button
              onClick={onClose}
              className="text-slate-400 hover:text-white p-1.5 rounded hover:bg-slate-800 transition"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Active Batch Banner */}
        <div className="bg-slate-900/60 border-b border-slate-800/80 px-6 py-2 flex items-center justify-between text-[11px] font-mono text-slate-400">
          <span>Active Scope: <strong className="text-slate-200">{activeBatchId || 'All Batches'}</strong></span>
          <span className="text-emerald-400 flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            Live Query Grounding Active
          </span>
        </div>

        {/* Chat Stream Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {/* Welcome / Empty Suggestions View */}
          {messages.length === 0 && (
            <div className="py-4 space-y-6">
              <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
                <div className="flex items-center gap-2 text-purple-400 font-semibold text-xs uppercase tracking-wider">
                  <Sparkles className="w-4 h-4" />
                  <span>How can I assist your reconciliation audit?</span>
                </div>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Ask any questions about financial records, amount variances, settlement discrepancies, or review statuses in the current analysis run.
                </p>
              </div>

              {/* Quick Prompt Cards */}
              <div className="space-y-2">
                <span className="text-[11px] font-mono uppercase tracking-wider text-slate-500 block">
                  Suggested Queries
                </span>
                <div className="grid grid-cols-1 gap-2">
                  {QUICK_SUGGESTIONS.map((sug, idx) => {
                    const Icon = sug.icon;
                    return (
                      <button
                        key={idx}
                        onClick={() => handleSend(sug.prompt)}
                        className="p-3 rounded-lg bg-slate-900/70 border border-slate-800/80 hover:border-purple-600/50 hover:bg-slate-900 text-left transition flex items-start gap-3 group"
                      >
                        <div className="p-1.5 rounded bg-slate-950 text-slate-400 group-hover:text-purple-400 border border-slate-850 mt-0.5">
                          <Icon className="w-3.5 h-3.5" />
                        </div>
                        <div className="flex-1">
                          <span className="text-xs font-semibold text-slate-200 block group-hover:text-white">
                            {sug.title}
                          </span>
                          <span className="text-[11px] text-slate-400 mt-0.5 line-clamp-1">
                            {sug.prompt}
                          </span>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

          {/* Conversation History */}
          {messages.map((msg) => {
            const isUser = msg.role === 'user';
            return (
              <div
                key={msg.id}
                className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}
              >
                <div
                  className={`max-w-[90%] rounded-xl p-4 text-xs shadow-md space-y-2 ${
                    isUser
                      ? 'bg-blue-600 text-white font-medium rounded-br-none'
                      : 'bg-slate-900 border border-slate-800 text-slate-200 rounded-bl-none'
                  }`}
                >
                  {!isUser && (
                    <div className="flex items-center justify-between border-b border-slate-800 pb-2 mb-2 text-[10px] font-mono text-purple-400">
                      <span className="flex items-center gap-1.5 font-semibold">
                        <BrainCircuit className="w-3 h-3" />
                        COPILOT ADVISORY
                      </span>
                      <span className="text-slate-500">{msg.timestamp}</span>
                    </div>
                  )}

                  {isUser ? (
                    <p className="leading-relaxed">{msg.content}</p>
                  ) : (
                    <div>{renderFormattedContent(msg.content)}</div>
                  )}

                  {/* Clickable Citations / Interactive Chips */}
                  {!isUser &&
                    ((msg.referencedTransactions && msg.referencedTransactions.length > 0) ||
                      (msg.referencedExceptions && msg.referencedExceptions.length > 0)) && (
                      <div className="pt-2 border-t border-slate-800 flex flex-wrap items-center gap-1.5 text-[11px] font-mono">
                        <span className="text-slate-500 text-[10px]">Citations:</span>
                        {msg.referencedTransactions?.map((tx) => (
                          <button
                            key={tx}
                            onClick={() => onSelectTransaction && onSelectTransaction(tx)}
                            className="px-2 py-0.5 rounded bg-blue-950 text-blue-300 border border-blue-800/80 hover:bg-blue-900 hover:text-white transition cursor-pointer flex items-center gap-1"
                            title="Click to view 3-way reconciliation drawer"
                          >
                            <span>{tx}</span>
                          </button>
                        ))}
                        {msg.referencedExceptions?.map((ex) => (
                          <span
                            key={ex}
                            className="px-2 py-0.5 rounded bg-rose-950 text-rose-300 border border-rose-800/80"
                          >
                            {ex}
                          </span>
                        ))}
                      </div>
                    )}
                </div>
                {isUser && (
                  <span className="text-[10px] font-mono text-slate-500 mt-1 mr-1">
                    {msg.timestamp}
                  </span>
                )}
              </div>
            );
          })}

          {/* In-Flight Thinking Spinner */}
          {isLoading && (
            <div className="flex items-center gap-3 p-3 rounded-lg bg-slate-900 border border-purple-900/50 text-xs text-purple-300 font-mono animate-pulse">
              <Loader2 className="w-4 h-4 animate-spin text-purple-400" />
              <span>Analyzing 3-way reconciliation evidence & active batch records...</span>
            </div>
          )}

          {/* Error Banner */}
          {error && (
            <div className="p-4 rounded-lg bg-rose-950/80 border border-rose-800 text-rose-200 text-xs flex items-start gap-3">
              <AlertTriangle className="w-4 h-4 text-rose-400 flex-shrink-0 mt-0.5" />
              <div className="space-y-1">
                <span className="font-semibold block">AI Copilot Notice</span>
                <p className="font-mono text-[11px]">{error}</p>
                {error.toLowerCase().includes('unconfigured') && (
                  <p className="text-[11px] text-slate-400 pt-1 border-t border-slate-800">
                    To enable live LLM assistance, ensure `GEMINI_API_KEY` or `OPENAI_API_KEY` is configured in your server `.env` file.
                  </p>
                )}
              </div>
            </div>
          )}

          <div ref={chatBottomRef} />
        </div>

        {/* Input Bar */}
        <div className="p-4 bg-slate-900 border-t border-slate-800 space-y-2">
          <div className="relative flex items-end gap-2 bg-slate-950 border border-slate-800 rounded-lg p-2 focus-within:border-purple-500/80 transition">
            <textarea
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask Copilot about transactions, discrepancies, or batch metrics... (Enter to send)"
              rows={2}
              className="w-full bg-transparent text-xs text-white placeholder-slate-500 focus:outline-none resize-none font-sans"
              disabled={isLoading}
            />
            <button
              onClick={() => handleSend()}
              disabled={!inputText.trim() || isLoading}
              className="p-2 rounded-md bg-purple-600 hover:bg-purple-500 text-white disabled:opacity-40 transition flex-shrink-0"
              title="Send query"
            >
              {isLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
            </button>
          </div>
          <div className="flex items-center justify-between text-[10px] font-mono text-slate-500 px-1">
            <span>Evidence-first advisory • Grounded in active batch</span>
            <span>Press Enter to send</span>
          </div>
        </div>
      </div>
    </div>
  );
};
