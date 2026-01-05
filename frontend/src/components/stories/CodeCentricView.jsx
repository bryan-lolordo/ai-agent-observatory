/**
 * CodeCentricView - Operation Code as Focal Point
 *
 * Displays the operation's code/prompt at the center with all related
 * issues, stories, and fixes surrounding it. Helps you know exactly
 * where in your code you need to make changes.
 *
 * Layout:
 * ┌─────────────────────────────────────────────────────────────────┐
 * │  Operation Header (name, call count, total cost)                │
 * ├─────────────────────────────────────────────────────────────────┤
 * │  ┌───────────────────────────────────────────────────────────┐  │
 * │  │  SYSTEM PROMPT (scrollable, syntax highlighted)           │  │
 * │  │  - The actual code/prompt from your operation             │  │
 * │  │  - Shows token count, model info                          │  │
 * │  └───────────────────────────────────────────────────────────┘  │
 * ├─────────────────────────────────────────────────────────────────┤
 * │  ISSUES DETECTED (connected to this code)                       │
 * │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐               │
 * │  │ 45 seq calls│ │ High cost   │ │ No caching  │               │
 * │  │ Latency     │ │ $0.04/call  │ │ 1.7s avg    │               │
 * │  └─────────────┘ └─────────────┘ └─────────────┘               │
 * ├─────────────────────────────────────────────────────────────────┤
 * │  FIXES FOR THIS CODE                                            │
 * │  ┌───────────────────────────────────────────────────────────┐  │
 * │  │ Fix: Enable Prompt Caching                                │  │
 * │  │ ┌─────────────────┐  ┌─────────────────┐                  │  │
 * │  │ │ BEFORE          │  │ AFTER           │                  │  │
 * │  │ │ your code here  │  │ fixed code here │                  │  │
 * │  │ └─────────────────┘  └─────────────────┘                  │  │
 * │  └───────────────────────────────────────────────────────────┘  │
 * └─────────────────────────────────────────────────────────────────┘
 */

import { useState, useMemo, useRef, useEffect } from 'react';
import {
  ChevronDown,
  ChevronRight,
  Copy,
  Check,
  AlertTriangle,
  Zap,
  DollarSign,
  Clock,
  Database,
  Code2,
  ArrowRight,
  Layers,
  MessageSquare,
  Send,
  X,
  Minimize2,
  Maximize2,
  Bot,
  User,
  Loader2
} from 'lucide-react';
import { STORY_THEMES } from '../../config/theme';
import { FIX_REPOSITORY, getFixesByCategory } from '../../config/fixes/repository';

// Story icon mapping
const STORY_ICONS = {
  latency: { icon: Clock, color: 'text-orange-400', bg: 'bg-orange-500/20' },
  cost: { icon: DollarSign, color: 'text-green-400', bg: 'bg-green-500/20' },
  cache: { icon: Database, color: 'text-blue-400', bg: 'bg-blue-500/20' },
  quality: { icon: Zap, color: 'text-purple-400', bg: 'bg-purple-500/20' },
  token: { icon: Layers, color: 'text-cyan-400', bg: 'bg-cyan-500/20' },
  prompt: { icon: Code2, color: 'text-pink-400', bg: 'bg-pink-500/20' },
  routing: { icon: ArrowRight, color: 'text-yellow-400', bg: 'bg-yellow-500/20' },
};

// ─────────────────────────────────────────────────────────────────────────────
// Scrollable Code Block Component
// ─────────────────────────────────────────────────────────────────────────────

function CodeBlock({ code, language = 'python', maxHeight = '300px', title, tokens, onCopy }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
    onCopy?.();
  };

  return (
    <div className="rounded-lg border border-gray-700 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-gray-800/80 border-b border-gray-700">
        <div className="flex items-center gap-3">
          <Code2 className="w-4 h-4 text-gray-400" />
          <span className="text-sm font-medium text-gray-300">{title}</span>
          {tokens && (
            <span className="text-xs px-2 py-0.5 rounded bg-gray-700 text-gray-400">
              {tokens.toLocaleString()} tokens
            </span>
          )}
        </div>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 px-2 py-1 rounded text-xs text-gray-400 hover:text-gray-200 hover:bg-gray-700 transition-colors"
        >
          {copied ? (
            <>
              <Check className="w-3.5 h-3.5 text-green-400" />
              <span className="text-green-400">Copied</span>
            </>
          ) : (
            <>
              <Copy className="w-3.5 h-3.5" />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>

      {/* Code Content */}
      <div
        className="overflow-auto bg-gray-900/50"
        style={{ maxHeight }}
      >
        <pre className="p-4 text-sm font-mono text-gray-300 whitespace-pre-wrap">
          {code || 'No code available'}
        </pre>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Issue Card Component
// ─────────────────────────────────────────────────────────────────────────────

function IssueCard({ issue, onClick }) {
  const storyConfig = STORY_ICONS[issue.storyId] || STORY_ICONS.latency;
  const Icon = storyConfig.icon;

  return (
    <div
      onClick={onClick}
      className={`p-4 rounded-lg border border-gray-700 cursor-pointer transition-all hover:border-gray-500 ${storyConfig.bg}`}
    >
      <div className="flex items-start gap-3">
        <div className={`p-2 rounded-lg bg-gray-800 ${storyConfig.color}`}>
          <Icon className="w-4 h-4" />
        </div>
        <div className="flex-1 min-w-0">
          <div className={`font-medium ${storyConfig.color}`}>{issue.title}</div>
          <div className="text-sm text-gray-400 mt-1">{issue.description}</div>
          {issue.metrics && (
            <div className="flex flex-wrap gap-2 mt-2">
              {issue.metrics.map((metric, i) => (
                <span key={i} className="text-xs px-2 py-0.5 rounded bg-gray-800 text-gray-300">
                  {metric}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Fix Card with Before/After Code
// ─────────────────────────────────────────────────────────────────────────────

function FixCard({ fix, operationData, expanded, onToggle }) {
  const [showCode, setShowCode] = useState(false);

  // Generate code and metrics based on operation data
  const generatedCode = useMemo(() => {
    if (fix.generateCode && operationData) {
      return fix.generateCode(operationData);
    }
    return { before: 'No code available', after: 'No code available' };
  }, [fix, operationData]);

  const generatedMetrics = useMemo(() => {
    if (fix.generateMetrics && operationData) {
      return fix.generateMetrics(operationData);
    }
    return [];
  }, [fix, operationData]);

  return (
    <div className="rounded-lg border border-gray-700 overflow-hidden bg-gray-900/30">
      {/* Fix Header */}
      <div
        onClick={onToggle}
        className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-800/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          {expanded ? (
            <ChevronDown className="w-4 h-4 text-gray-500" />
          ) : (
            <ChevronRight className="w-4 h-4 text-gray-500" />
          )}
          <div>
            <div className="font-medium text-gray-200">{fix.title}</div>
            <div className="text-sm text-gray-500">{fix.subtitle}</div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className={`text-xs px-2 py-0.5 rounded ${fix.effortColor} bg-gray-800`}>
            {fix.effort} Effort
          </span>
          {/* Show potential savings from metrics */}
          {generatedMetrics.length > 0 && generatedMetrics[0].changePercent && (
            <span className="text-sm font-medium text-green-400">
              {generatedMetrics[0].changePercent}% {generatedMetrics[0].label}
            </span>
          )}
        </div>
      </div>

      {/* Expanded Content */}
      {expanded && (
        <div className="border-t border-gray-700 p-4 space-y-4">
          {/* Metrics Preview */}
          {generatedMetrics.length > 0 && (
            <div className="grid grid-cols-3 gap-4">
              {generatedMetrics.map((metric, i) => (
                <div key={i} className="p-3 rounded bg-gray-800/50 text-center">
                  <div className="text-xs text-gray-500 uppercase">{metric.label}</div>
                  <div className="flex items-center justify-center gap-2 mt-1">
                    <span className="text-gray-400 line-through text-sm">{metric.before}</span>
                    <ArrowRight className="w-3 h-3 text-gray-600" />
                    <span className="text-green-400 font-medium">{metric.after}</span>
                  </div>
                  {metric.changePercent !== 0 && (
                    <div className={`text-xs mt-1 ${metric.changePercent < 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {metric.changePercent > 0 ? '+' : ''}{metric.changePercent}%
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Toggle Code View */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              setShowCode(!showCode);
            }}
            className="flex items-center gap-2 text-sm text-cyan-400 hover:text-cyan-300 transition-colors"
          >
            <Code2 className="w-4 h-4" />
            {showCode ? 'Hide Code Changes' : 'Show Code Changes'}
          </button>

          {/* Before/After Code */}
          {showCode && (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-xs text-red-400 uppercase tracking-wide mb-2 flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-red-500"></span>
                  Before
                </div>
                <pre className="p-3 rounded bg-gray-950 border border-red-900/30 text-sm font-mono text-gray-400 overflow-auto max-h-48">
                  {generatedCode.before}
                </pre>
              </div>
              <div>
                <div className="text-xs text-green-400 uppercase tracking-wide mb-2 flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-green-500"></span>
                  After
                </div>
                <pre className="p-3 rounded bg-gray-950 border border-green-900/30 text-sm font-mono text-gray-300 overflow-auto max-h-48">
                  {generatedCode.after}
                </pre>
              </div>
            </div>
          )}

          {/* Benefits & Tradeoffs */}
          <div className="grid grid-cols-2 gap-4 pt-2">
            <div>
              <div className="text-xs text-gray-500 uppercase tracking-wide mb-2">Benefits</div>
              <ul className="space-y-1">
                {fix.benefits?.slice(0, 3).map((b, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-gray-400">
                    <Check className="w-3.5 h-3.5 text-green-500 mt-0.5 flex-shrink-0" />
                    {b}
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <div className="text-xs text-gray-500 uppercase tracking-wide mb-2">Tradeoffs</div>
              <ul className="space-y-1">
                {fix.tradeoffs?.slice(0, 3).map((t, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-gray-400">
                    <AlertTriangle className="w-3.5 h-3.5 text-yellow-500 mt-0.5 flex-shrink-0" />
                    {t}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Feedback ChatBot Component
// ─────────────────────────────────────────────────────────────────────────────

function FeedbackChatBot({ operation, operationData, systemPrompt, issues }) {
  const [isOpen, setIsOpen] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Focus input when chat opens
  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  // Generate initial context message when opening
  useEffect(() => {
    if (isOpen && messages.length === 0) {
      const contextMessage = generateContextMessage();
      setMessages([{
        role: 'assistant',
        content: contextMessage,
        timestamp: new Date(),
      }]);
    }
  }, [isOpen, operation]);

  const generateContextMessage = () => {
    const issueCount = issues?.length || 0;
    const callCount = operationData?.call_count || 0;
    const totalCost = operationData?.total_cost || 0;
    const avgLatency = operationData?.avg_latency_ms || 0;

    let message = `I'm analyzing **${operation}**.\n\n`;
    message += `**Quick Stats:**\n`;
    message += `- ${callCount} calls total\n`;
    message += `- $${totalCost.toFixed(2)} total cost\n`;
    message += `- ${(avgLatency / 1000).toFixed(1)}s avg latency\n\n`;

    if (issueCount > 0) {
      message += `**${issueCount} issues detected:**\n`;
      issues.slice(0, 3).forEach(issue => {
        message += `- ${issue.title}\n`;
      });
      message += `\n`;
    }

    message += `What would you like to know? I can help with:\n`;
    message += `- Explaining detected issues\n`;
    message += `- Suggesting optimizations\n`;
    message += `- Reviewing your system prompt\n`;
    message += `- Estimating impact of changes`;

    return message;
  };

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage = {
      role: 'user',
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      // Build context for the API
      const context = {
        operation,
        systemPrompt: systemPrompt?.slice(0, 2000), // Limit prompt size
        issues: issues?.map(i => ({ title: i.title, description: i.description })),
        metrics: {
          call_count: operationData?.call_count,
          total_cost: operationData?.total_cost,
          avg_latency_ms: operationData?.avg_latency_ms,
          system_prompt_tokens: operationData?.system_prompt_tokens,
        },
        conversation: messages.slice(-6).map(m => ({ role: m.role, content: m.content })),
        userQuery: input.trim(),
      };

      const response = await fetch('/api/chat/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(context),
      });

      if (response.ok) {
        const data = await response.json();
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: data.response || data.message || 'I apologize, I could not generate a response.',
          timestamp: new Date(),
        }]);
      } else {
        // Fallback: Generate a helpful response locally
        const fallbackResponse = generateFallbackResponse(input.trim());
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: fallbackResponse,
          timestamp: new Date(),
        }]);
      }
    } catch (err) {
      // Fallback for network errors
      const fallbackResponse = generateFallbackResponse(input.trim());
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: fallbackResponse,
        timestamp: new Date(),
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const generateFallbackResponse = (query) => {
    const q = query.toLowerCase();

    if (q.includes('cost') || q.includes('expensive') || q.includes('money')) {
      const cost = operationData?.total_cost || 0;
      const calls = operationData?.call_count || 1;
      const perCall = cost / calls;
      return `**Cost Analysis for ${operation}:**\n\n` +
        `- Total cost: $${cost.toFixed(2)}\n` +
        `- Cost per call: $${perCall.toFixed(4)}\n` +
        `- ${calls} total calls\n\n` +
        `**Recommendations:**\n` +
        `1. Consider prompt caching to reduce repeat token costs\n` +
        `2. Use a smaller model for simpler queries\n` +
        `3. Batch similar requests together`;
    }

    if (q.includes('latency') || q.includes('slow') || q.includes('speed') || q.includes('fast')) {
      const latency = operationData?.avg_latency_ms || 0;
      return `**Latency Analysis for ${operation}:**\n\n` +
        `- Average latency: ${(latency / 1000).toFixed(1)}s\n\n` +
        `**Recommendations:**\n` +
        `1. Enable streaming for better perceived performance\n` +
        `2. Reduce system prompt size if possible\n` +
        `3. Consider using a faster model for simple operations\n` +
        `4. Parallelize independent LLM calls`;
    }

    if (q.includes('prompt') || q.includes('system')) {
      const tokens = operationData?.system_prompt_tokens || 0;
      return `**System Prompt Analysis:**\n\n` +
        `- Current size: ${tokens.toLocaleString()} tokens\n\n` +
        `**Recommendations:**\n` +
        `1. Remove redundant instructions\n` +
        `2. Use concise examples instead of verbose ones\n` +
        `3. Move static content to prompt cache\n` +
        `4. Consider splitting into focused sub-prompts`;
    }

    if (q.includes('cache') || q.includes('caching')) {
      return `**Caching Recommendations for ${operation}:**\n\n` +
        `1. **Prompt Caching**: Your system prompt appears static - enable Anthropic/OpenAI prompt caching\n` +
        `2. **Response Caching**: Cache responses for identical inputs\n` +
        `3. **Semantic Caching**: Cache similar queries using embeddings\n\n` +
        `Expected savings: 30-60% on token costs`;
    }

    if (q.includes('issue') || q.includes('problem') || q.includes('fix')) {
      if (issues?.length > 0) {
        let response = `**Detected Issues for ${operation}:**\n\n`;
        issues.forEach((issue, i) => {
          response += `${i + 1}. **${issue.title}**\n   ${issue.description}\n\n`;
        });
        return response;
      }
      return `No significant issues detected for ${operation}. The operation appears to be running efficiently.`;
    }

    // Default response
    return `I can help you analyze **${operation}**. Try asking about:\n\n` +
      `- "How can I reduce costs?"\n` +
      `- "Why is this operation slow?"\n` +
      `- "How can I optimize the system prompt?"\n` +
      `- "Should I enable caching?"\n` +
      `- "What issues should I fix first?"`;
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const quickActions = [
    { label: 'Reduce costs', query: 'How can I reduce the cost of this operation?' },
    { label: 'Speed up', query: 'How can I make this operation faster?' },
    { label: 'Fix issues', query: 'What issues should I fix first?' },
    { label: 'Review prompt', query: 'Can you review my system prompt?' },
  ];

  // Collapsed button
  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 flex items-center gap-2 px-4 py-3 rounded-full bg-gradient-to-r from-cyan-600 to-blue-600 text-white shadow-lg hover:shadow-xl transition-all hover:scale-105 z-50"
      >
        <MessageSquare className="w-5 h-5" />
        <span className="font-medium">Get Feedback</span>
      </button>
    );
  }

  // Chat panel
  return (
    <div
      className={`fixed bottom-6 right-6 flex flex-col bg-gray-900 border border-gray-700 rounded-xl shadow-2xl z-50 transition-all ${
        isExpanded ? 'w-[600px] h-[500px]' : 'w-[400px] h-[400px]'
      }`}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700 bg-gradient-to-r from-cyan-600/20 to-blue-600/20 rounded-t-xl">
        <div className="flex items-center gap-2">
          <Bot className="w-5 h-5 text-cyan-400" />
          <span className="font-medium text-gray-200">Optimization Assistant</span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-1.5 rounded hover:bg-gray-700 text-gray-400 hover:text-gray-200 transition-colors"
            title={isExpanded ? 'Minimize' : 'Expand'}
          >
            {isExpanded ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>
          <button
            onClick={() => setIsOpen(false)}
            className="p-1.5 rounded hover:bg-gray-700 text-gray-400 hover:text-gray-200 transition-colors"
            title="Close"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}
          >
            <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
              msg.role === 'user' ? 'bg-blue-600' : 'bg-cyan-600'
            }`}>
              {msg.role === 'user' ? (
                <User className="w-4 h-4 text-white" />
              ) : (
                <Bot className="w-4 h-4 text-white" />
              )}
            </div>
            <div className={`max-w-[80%] rounded-lg px-3 py-2 ${
              msg.role === 'user'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-800 text-gray-200'
            }`}>
              <div className="text-sm whitespace-pre-wrap">
                {msg.content.split('**').map((part, j) =>
                  j % 2 === 1 ? <strong key={j}>{part}</strong> : part
                )}
              </div>
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex gap-3">
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-cyan-600 flex items-center justify-center">
              <Bot className="w-4 h-4 text-white" />
            </div>
            <div className="bg-gray-800 rounded-lg px-3 py-2">
              <Loader2 className="w-4 h-4 text-cyan-400 animate-spin" />
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Quick Actions */}
      {messages.length <= 1 && (
        <div className="px-4 pb-2">
          <div className="flex flex-wrap gap-2">
            {quickActions.map((action, i) => (
              <button
                key={i}
                onClick={() => {
                  setInput(action.query);
                  setTimeout(() => handleSend(), 100);
                }}
                className="text-xs px-2 py-1 rounded-full bg-gray-800 text-gray-400 hover:text-gray-200 hover:bg-gray-700 transition-colors"
              >
                {action.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input */}
      <div className="p-3 border-t border-gray-700">
        <div className="flex items-center gap-2">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about this operation..."
            className="flex-1 px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-gray-200 placeholder-gray-500 focus:outline-none focus:border-cyan-500 text-sm"
            disabled={isLoading}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            className="p-2 rounded-lg bg-cyan-600 text-white hover:bg-cyan-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Main Component
// ─────────────────────────────────────────────────────────────────────────────

export default function CodeCentricView({
  operation,           // Operation name
  operationData,       // Aggregated data for this operation (calls, metrics, etc.)
  systemPrompt,        // The system prompt text
  systemPromptTokens,  // Token count
  issues = [],         // Detected issues [{storyId, title, description, metrics}]
  onIssueClick,        // Handler when clicking an issue
  onFixApply,          // Handler when applying a fix
  loadingPrompt = false, // Whether system prompt is loading
}) {
  const [expandedFixes, setExpandedFixes] = useState({});

  // Get applicable fixes based on issues
  const applicableFixes = useMemo(() => {
    const fixSet = new Set();
    const fixes = [];

    issues.forEach(issue => {
      const storyFixes = getFixesByCategory(issue.storyId);
      storyFixes.forEach(fix => {
        if (!fixSet.has(fix.id)) {
          // Check if fix is applicable to this data
          if (fix.applicableWhen?.(operationData || {})) {
            fixSet.add(fix.id);
            fixes.push({ ...fix, sourceIssue: issue });
          }
        }
      });
    });

    return fixes;
  }, [issues, operationData]);

  const toggleFix = (fixId) => {
    setExpandedFixes(prev => ({
      ...prev,
      [fixId]: !prev[fixId]
    }));
  };

  // Calculate aggregate stats
  const stats = useMemo(() => {
    if (!operationData) return null;
    return {
      totalCalls: operationData.call_count || operationData.calls?.length || 0,
      totalCost: operationData.total_cost || 0,
      avgLatency: operationData.avg_latency_ms || operationData.latency_ms || 0,
      model: operationData.model_name || 'Unknown',
    };
  }, [operationData]);

  return (
    <div className="space-y-6">
      {/* Operation Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-100 font-mono">{operation}</h2>
          <p className="text-sm text-gray-500 mt-1">
            Code-centric view - Your operation code with related issues and fixes
          </p>
        </div>
        {stats && (
          <div className="flex items-center gap-4">
            <div className="text-right">
              <div className="text-sm text-gray-500">Calls</div>
              <div className="text-lg font-medium text-gray-200">{stats.totalCalls}</div>
            </div>
            <div className="text-right">
              <div className="text-sm text-gray-500">Total Cost</div>
              <div className="text-lg font-medium text-green-400">${stats.totalCost.toFixed(2)}</div>
            </div>
            <div className="text-right">
              <div className="text-sm text-gray-500">Avg Latency</div>
              <div className="text-lg font-medium text-orange-400">{(stats.avgLatency / 1000).toFixed(1)}s</div>
            </div>
          </div>
        )}
      </div>

      {/* ═══════════════════════════════════════════════════════════════════════ */}
      {/* SECTION 1: THE CODE (Main Focal Point) */}
      {/* ═══════════════════════════════════════════════════════════════════════ */}

      <div className="space-y-2">
        <div className="flex items-center gap-2 text-sm text-gray-400">
          <Code2 className="w-4 h-4" />
          <span className="uppercase tracking-wide">Your Operation Code</span>
          {loadingPrompt && (
            <span className="text-xs text-cyan-400 flex items-center gap-1">
              <span className="w-3 h-3 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin"></span>
              Loading...
            </span>
          )}
        </div>

        {loadingPrompt ? (
          <div className="rounded-lg border border-gray-700 bg-gray-900/50 p-8">
            <div className="animate-pulse space-y-3">
              <div className="h-4 bg-gray-700 rounded w-3/4"></div>
              <div className="h-4 bg-gray-700 rounded w-1/2"></div>
              <div className="h-4 bg-gray-700 rounded w-5/6"></div>
              <div className="h-4 bg-gray-700 rounded w-2/3"></div>
            </div>
          </div>
        ) : systemPrompt ? (
          <CodeBlock
            code={systemPrompt}
            title="System Prompt"
            tokens={systemPromptTokens}
            maxHeight="350px"
          />
        ) : (
          <div className="rounded-lg border border-gray-700 bg-gray-900/50 p-8 text-center">
            <Code2 className="w-8 h-8 text-gray-600 mx-auto mb-3" />
            <p className="text-gray-500">No system prompt found for this operation</p>
            <p className="text-xs text-gray-600 mt-1">
              The calls for this operation may not have a system prompt stored
            </p>
          </div>
        )}
      </div>

      {/* ═══════════════════════════════════════════════════════════════════════ */}
      {/* SECTION 2: ISSUES DETECTED */}
      {/* ═══════════════════════════════════════════════════════════════════════ */}

      {issues.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-sm text-gray-400">
            <AlertTriangle className="w-4 h-4 text-yellow-500" />
            <span className="uppercase tracking-wide">Issues Detected</span>
            <span className="text-xs px-2 py-0.5 rounded bg-yellow-500/20 text-yellow-400">
              {issues.length} issues
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {issues.map((issue, i) => (
              <IssueCard
                key={i}
                issue={issue}
                onClick={() => onIssueClick?.(issue)}
              />
            ))}
          </div>
        </div>
      )}

      {/* ═══════════════════════════════════════════════════════════════════════ */}
      {/* SECTION 3: FIXES FOR THIS CODE */}
      {/* ═══════════════════════════════════════════════════════════════════════ */}

      {applicableFixes.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-sm text-gray-400">
            <Zap className="w-4 h-4 text-cyan-500" />
            <span className="uppercase tracking-wide">Fixes for This Code</span>
            <span className="text-xs px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-400">
              {applicableFixes.length} available
            </span>
          </div>

          <div className="space-y-3">
            {applicableFixes.map((fix) => (
              <FixCard
                key={fix.id}
                fix={fix}
                operationData={operationData}
                expanded={expandedFixes[fix.id]}
                onToggle={() => toggleFix(fix.id)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Empty State */}
      {issues.length === 0 && (
        <div className="p-8 text-center rounded-lg border border-gray-700 bg-gray-900/30">
          <Check className="w-8 h-8 text-green-500 mx-auto mb-3" />
          <div className="text-gray-300 font-medium">No Issues Detected</div>
          <div className="text-sm text-gray-500 mt-1">
            This operation looks well-optimized!
          </div>
        </div>
      )}

      {/* Feedback ChatBot */}
      <FeedbackChatBot
        operation={operation}
        operationData={operationData}
        systemPrompt={systemPrompt}
        issues={issues}
      />
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Helper: Generate issues from operation data
// ─────────────────────────────────────────────────────────────────────────────

export function generateIssuesFromOperation(operationData) {
  const issues = [];

  if (!operationData) return issues;

  // Check for sequential calls that could be batched
  const callCount = operationData.call_count || operationData.calls?.length || 0;
  if (callCount > 10) {
    issues.push({
      storyId: 'latency',
      title: `${callCount} Sequential Calls`,
      description: 'Consider batching or parallelizing these calls',
      metrics: [
        `${callCount} calls`,
        `$${((operationData.total_cost || 0) / callCount).toFixed(4)}/call`,
        `${((operationData.avg_latency_ms || 0) / 1000).toFixed(1)}s avg`
      ]
    });
  }

  // Check for high cost
  if ((operationData.total_cost || 0) > 1) {
    issues.push({
      storyId: 'cost',
      title: 'High Cost Operation',
      description: `Total cost: $${(operationData.total_cost || 0).toFixed(2)}`,
      metrics: [
        `$${(operationData.total_cost || 0).toFixed(2)} total`,
        `${callCount} calls`
      ]
    });
  }

  // Check for cache opportunity
  if (!operationData.cache_hit && (operationData.system_prompt_tokens || 0) > 200) {
    issues.push({
      storyId: 'cache',
      title: 'No Caching Detected',
      description: 'Static system prompt could be cached',
      metrics: [
        `${(operationData.system_prompt_tokens || 0).toLocaleString()} prompt tokens`,
        'Cache available'
      ]
    });
  }

  // Check for high latency
  if ((operationData.avg_latency_ms || operationData.latency_ms || 0) > 2000) {
    issues.push({
      storyId: 'latency',
      title: 'Slow Response Time',
      description: 'Average latency exceeds 2 seconds',
      metrics: [
        `${((operationData.avg_latency_ms || operationData.latency_ms || 0) / 1000).toFixed(1)}s avg`,
        'Consider streaming'
      ]
    });
  }

  // Check for large system prompt
  if ((operationData.system_prompt_tokens || 0) > 500) {
    issues.push({
      storyId: 'prompt',
      title: 'Large System Prompt',
      description: 'System prompt may be verbose',
      metrics: [
        `${(operationData.system_prompt_tokens || 0).toLocaleString()} tokens`,
        'Consider compression'
      ]
    });
  }

  // Check for token imbalance
  const ratio = (operationData.prompt_tokens || 1) / (operationData.completion_tokens || 1);
  if (ratio > 20) {
    issues.push({
      storyId: 'token',
      title: 'Token Imbalance',
      description: `High input/output ratio (${ratio.toFixed(0)}:1)`,
      metrics: [
        `${ratio.toFixed(0)}:1 ratio`,
        'Output may be too brief'
      ]
    });
  }

  return issues;
}
