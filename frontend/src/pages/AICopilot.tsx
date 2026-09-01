import * as React from 'react';
import { useState } from 'react';
import { useUsers } from '@/api';
import { cn } from '@/utils';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { ScrollArea } from '@/components/ui/ScrollArea';
import { Send, Bot, User, Loader2, AlertCircle, CheckCircle, Sparkles, Copy, ChevronUp, ChevronDown } from 'lucide-react';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  context_used?: Record<string, any>;
}

interface CopilotResponse {
  response: string;
  intent: string;
  context_used: Record<string, any>;
  ai_available: boolean;
}

const EXAMPLE_QUERIES = [
  "Why was transaction 121 flagged?",
  "Why is Raj's Trust Score 76.4?",
  "What indicators contributed to this anomaly?",
  "Summarize this user's recent behaviour.",
  "Why did this payment receive HIGH risk?",
  "Explain the difference between Trust Score and Fraud Risk.",
  "Show me the recent suspicious activity.",
  "What is the model's precision and recall?",
];

export function AICopilot() {
  const { data: usersData, isLoading: usersLoading } = useUsers(50);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null);
  const [selectedTransactionId, setSelectedTransactionId] = useState<number | null>(null);
  const [selectedPaymentId, setSelectedPaymentId] = useState<number | null>(null);
  const [showExamples, setShowExamples] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copilotStatus, setCopilotStatus] = useState<{ available: boolean; provider: string | null }>({
    available: false,
    provider: null,
  });
  const messagesEndRef = React.useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  React.useEffect(() => {
    scrollToBottom();
  }, [messages]);

  React.useEffect(() => {
    checkCopilotStatus();
  }, []);

  const checkCopilotStatus = async () => {
    try {
      const response = await fetch('/api/copilot/status');
      const data = await response.json();
      setCopilotStatus(data);
    } catch {
      setCopilotStatus({ available: false, provider: null });
    }
  };

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userQuery = input.trim();
    setInput('');
    setError(null);
    setIsLoading(true);

    const userMessage: ChatMessage = {
      role: 'user',
      content: userQuery,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setShowExamples(false);

    try {
      const conversationHistory = messages.slice(-10).map((m) => ({
        user: m.role === 'user' ? m.content : undefined,
        assistant: m.role === 'assistant' ? m.content : undefined,
      })).filter((m) => m.user || m.assistant);

      const response = await fetch('/api/copilot/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: userQuery,
          user_id: selectedUserId,
          transaction_id: selectedTransactionId,
          payment_id: selectedPaymentId,
          conversation_history: conversationHistory,
        }),
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || `HTTP ${response.status}`);
      }

      const data: CopilotResponse = await response.json();

      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: data.response,
        timestamp: new Date().toISOString(),
        context_used: data.context_used,
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err: any) {
      setError(err.message || 'Failed to get response from AI Copilot');
      const errorMessage: ChatMessage = {
        role: 'assistant',
        content: `⚠️ Error: ${err.message || 'Unknown error'}`,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleExampleClick = (query: string) => {
    setInput(query);
  };

  const handleClearChat = () => {
    setMessages([]);
    setShowExamples(true);
    setError(null);
  };

  const copyResponse = (content: string) => {
    navigator.clipboard.writeText(content);
  };

  const users = usersData?.users ?? [];

  return (
    <div className="space-y-6 h-[calc(100vh-200px)] flex flex-col">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-text">AI Risk Analyst Copilot</h1>
          <p className="text-text-muted mt-1">
            Ask questions about TrustBridge risk intelligence using real data context.
            {copilotStatus.available ? ' ✓ Connected' : ' ⚠ Configure AI_API_KEY in .env to enable'}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Badge variant={copilotStatus.available ? 'success' : 'warning'} className="gap-1">
            {copilotStatus.available ? (
              <>
                <CheckCircle className="w-3 h-3" />
                {copilotStatus.provider?.toUpperCase()} Connected
              </>
            ) : (
              <>
                <AlertCircle className="w-3 h-3" />
                AI Unavailable
              </>
            )}
          </Badge>
          <Button variant="secondary" onClick={handleClearChat} disabled={messages.length === 0}>
            Clear Chat
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 flex-1 min-h-0">
        {/* Context Panel */}
        <div className="lg:col-span-1 space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Sparkles className="w-5 h-5" />
                Context Selection
              </CardTitle>
              <CardDescription>Select entities to ground the AI's answers in real data</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-text-muted mb-2">User Profile</label>
                <select
                  value={selectedUserId?.toString() || ''}
                  onChange={(e) => {
                    const val = e.target.value;
                    setSelectedUserId(val ? Number(val) : null);
                    setSelectedTransactionId(null);
                    setSelectedPaymentId(null);
                  }}
                  className="input"
                >
                  <option value="">None (General Questions)</option>
                  {users.map((u) => (
                    <option key={u.id} value={u.id.toString()}>
                      {u.name} (ID: {u.id})
                    </option>
                  ))}
                </select>
                {selectedUserId && (
                  <p className="text-xs text-text-muted mt-1">
                    {users.find((u) => u.id === selectedUserId)?.name} selected
                  </p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-text-muted mb-2">Transaction ID (Optional)</label>
                <Input
                  type="number"
                  placeholder="e.g., 121"
                  value={selectedTransactionId?.toString() || ''}
                  onChange={(e) => setSelectedTransactionId(e.target.value ? Number(e.target.value) : null)}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-text-muted mb-2">Payment ID (Optional)</label>
                <Input
                  type="number"
                  placeholder="e.g., 5"
                  value={selectedPaymentId?.toString() || ''}
                  onChange={(e) => setSelectedPaymentId(e.target.value ? Number(e.target.value) : null)}
                />
              </div>

              {selectedUserId && (
                <div className="p-3 bg-primary-bg border border-primary-border rounded-lg">
                  <p className="text-xs text-primary font-medium">Context Active</p>
                  <p className="text-xs text-text-muted mt-1">
                    AI will reference this user's trust score, transactions, and risk events.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Bot className="w-5 h-5" />
                Example Questions
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {EXAMPLE_QUERIES.map((q, i) => (
                <button
                  key={i}
                  onClick={() => handleExampleClick(q)}
                  className="w-full text-left p-3 bg-bg-elevated/50 border border-border/50 rounded-lg hover:border-primary/50 hover:bg-primary-bg/50 transition-colors text-sm text-text"
                >
                  {q}
                </button>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AlertCircle className="w-5 h-5 text-amber-400" />
                Limitations
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-xs text-text-muted">
              <p>• Synthetic demo data (399 transactions, 2 injected anomalies)</p>
              <p>• Isolation Forest unsupervised model — indicators ≠ causes</p>
              <p>• Trust Score ≠ Fraud Risk (different concepts)</p>
              <p>• Payment methods are SIMULATED</p>
              <p>• Read-only — cannot execute actions</p>
            </CardContent>
          </Card>
        </div>

        {/* Chat Panel */}
        <div className="lg:col-span-3 flex flex-col min-h-0">
          <Card className="flex-1 flex flex-col min-h-0">
            <CardHeader className="flex-shrink-0">
              <CardTitle className="flex items-center gap-2">
                <Bot className="w-5 h-5" />
                Conversation
              </CardTitle>
            </CardHeader>
            <CardContent className="flex-1 min-h-0 p-0">
              <ScrollArea className="h-full p-4 space-y-4">
                {showExamples && messages.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-64 text-text-muted">
                    <Bot className="w-16 h-16 mb-4 text-text-subtle" />
                    <h3 className="text-lg font-medium text-text mb-2">Welcome to TrustBridge AI Copilot</h3>
                    <p className="text-center max-w-md mb-6">
                      Ask me about trust scores, fraud flags, ML anomalies, payment risk decisions,
                      ledger entries, or model performance. Select a user above for personalized context.
                    </p>
                    <div className="flex flex-wrap gap-2 justify-center">
                      {EXAMPLE_QUERIES.slice(0, 4).map((q, i) => (
                        <button
                          key={i}
                          onClick={() => handleExampleClick(q)}
                          className="px-4 py-2 bg-bg-elevated border border-border rounded-lg text-sm hover:border-primary/50 transition-colors"
                        >
                          {q}
                        </button>
                      ))}
                    </div>
                  </div>
                ) : (
                  <>
                    {messages.map((msg, idx) => (
                      <div key={idx} className={cn('flex gap-3', msg.role === 'user' ? 'flex-row-reverse' : '')}>
                        <div
                          className={cn(
                            'w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0',
                            msg.role === 'user' ? 'bg-primary/20' : 'bg-purple-500/20'
                          )}
                        >
                          {msg.role === 'user' ? (
                            <User className="w-4 h-4 text-primary" />
                          ) : (
                            <Bot className="w-4 h-4 text-purple-400" />
                          )}
                        </div>
                        <div
                          className={cn(
                            'max-w-[70%] p-4 rounded-2xl',
                            msg.role === 'user'
                              ? 'bg-primary-bg border border-primary-border rounded-br-sm'
                              : 'bg-bg-elevated/50 border border-border/50 rounded-bl-sm'
                          )}
                        >
                          <div className="prose prose-sm dark prose-invert max-w-none">
                            <p className="whitespace-pre-wrap text-text">{msg.content}</p>
                          </div>
                          <div className="flex items-center gap-2 mt-2">
                            <span className="text-[10px] text-text-muted">
                              {new Date(msg.timestamp).toLocaleTimeString()}
                            </span>
                            {msg.role === 'assistant' && (
                              <button
                                onClick={() => copyResponse(msg.content)}
                                className="p-1 text-text-muted hover:text-primary transition-colors"
                                title="Copy response"
                              >
                                <Copy className="w-3 h-3" />
                              </button>
                            )}
                            {msg.context_used && Object.keys(msg.context_used).length > 0 && (
                              <button
                                className="p-1 text-text-muted hover:text-primary transition-colors"
                                title="View context used"
                              >
                                <ChevronDown className="w-3 h-3" />
                              </button>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                    <div ref={messagesEndRef} />
                  </>
                )}
              </ScrollArea>

              {isLoading && (
                <div className="p-4 border-t border-border flex items-center gap-3 bg-bg-elevated/30">
                  <Loader2 className="w-5 h-5 text-primary animate-spin" />
                  <span className="text-text-muted">AI is analyzing TrustBridge data...</span>
                </div>
              )}

              {error && (
                <div className="p-4 border-t border-danger-border bg-danger-bg/50">
                  <p className="text-sm text-danger flex items-center gap-2">
                    <AlertCircle className="w-4 h-4" />
                    {error}
                  </p>
                </div>
              )}
            </CardContent>

            <CardHeader className="flex-shrink-0 border-t border-border">
              <form onSubmit={handleSend} className="w-full">
                <div className="flex gap-2">
                  <Input
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Ask about trust scores, fraud flags, anomalies, payments, ledger..."
                    disabled={isLoading}
                    className="flex-1"
                    onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), handleSend(e))}
                  />
                  <Button type="submit" disabled={isLoading || !input.trim()} className="flex-shrink-0">
                    {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                  </Button>
                </div>
                <p className="text-xs text-text-muted mt-2">
                  Press Enter to send, Shift+Enter for new line. AI uses server-side provider only — keys never leave backend.
                </p>
              </form>
            </CardHeader>
          </Card>
        </div>
      </div>
    </div>
  );
}