import * as React from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Table, Column } from '@/components/ui/Table';
import { Copy, ExternalLink, FileCode, Terminal, Server, Database, Shield, Code, Globe, Key } from 'lucide-react';

const ENDPOINTS = [
  { method: 'GET', path: '/api/health', description: 'Health check', tags: ['System'] },
  { method: 'GET', path: '/api/dashboard/summary', description: 'Dashboard summary metrics', tags: ['Dashboard'] },
  { method: 'GET', path: '/api/dashboard/live-risk-feed', description: 'Live risk event feed', tags: ['Dashboard'] },
  { method: 'GET', path: '/api/dashboard/recent-transactions', description: 'Recent transactions', tags: ['Dashboard'] },
  { method: 'GET', path: '/api/users', description: 'List all users (paginated)', tags: ['Users'] },
  { method: 'GET', path: '/api/users/:id', description: 'Get user by ID', tags: ['Users'] },
  { method: 'GET', path: '/api/users/:id/trust', description: 'Get user trust score', tags: ['Users', 'Trust'] },
  { method: 'GET', path: '/api/users/:id/transactions', description: 'Get user transactions', tags: ['Users', 'Transactions'] },
  { method: 'GET', path: '/api/users/:id/payments', description: 'Get user payment history', tags: ['Users', 'Payments'] },
  { method: 'POST', path: '/api/risk/assess', description: 'Assess payment risk', tags: ['Risk', 'Assessment'] },
  { method: 'GET', path: '/api/risk/events', description: 'List risk events', tags: ['Risk', 'Events'] },
  { method: 'GET', path: '/api/risk/events/:id', description: 'Get risk event detail', tags: ['Risk', 'Events'] },
  { method: 'GET', path: '/api/risk/evaluation', description: 'ML model evaluation', tags: ['Risk', 'ML'] },
  { method: 'GET', path: '/api/risk/comparison', description: 'Rule vs ML comparison', tags: ['Risk', 'ML'] },
  { method: 'GET', path: '/api/risk/explain/:id', description: 'Explain risk event', tags: ['Risk', 'Explainability'] },
  { method: 'POST', path: '/api/payments/simulate', description: 'Simulate payment', tags: ['Payments'] },
  { method: 'GET', path: '/api/payments', description: 'List payments', tags: ['Payments'] },
  { method: 'GET', path: '/api/payments/:id', description: 'Get payment detail', tags: ['Payments'] },
  { method: 'GET', path: '/api/payments/by-idempotency/:key', description: 'Get payment by idempotency key', tags: ['Payments'] },
  { method: 'GET', path: '/api/payments/by-reference/:ref', description: 'Get payment by reference ID', tags: ['Payments'] },
  { method: 'GET', path: '/api/ledger/:id', description: 'Get ledger entries', tags: ['Ledger'] },
  { method: 'GET', path: '/api/ledger/:id/verify', description: 'Verify ledger balance', tags: ['Ledger'] },
  { method: 'GET', path: '/api/accounts/:id/payments', description: 'Get account payments', tags: ['Accounts', 'Payments'] },
];

const METHOD_COLORS: Record<string, string> = {
  GET: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  POST: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  PUT: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  DELETE: 'bg-red-500/10 text-red-400 border-red-500/20',
  PATCH: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
};

export function Developers() {
  const [copied, setCopied] = React.useState<string | null>(null);

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(text);
    setTimeout(() => setCopied(null), 2000);
  };

  const baseUrl = 'http://localhost:8000';

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-text">Developers</h1>
        <p className="text-text-muted mt-1">API reference, integration guides, and development resources</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Server className="w-5 h-5 text-blue-400" />
              Base URL
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="p-3 bg-bg-elevated/50 rounded-lg border border-border/50 flex items-center justify-between">
              <code className="font-mono text-sm text-text">{baseUrl}/api</code>
              <button
                onClick={() => copyToClipboard(`${baseUrl}/api`)}
                className="p-1.5 text-text-muted hover:text-primary transition-colors"
                title="Copy base URL"
              >
                <Copy className="w-4 h-4" />
              </button>
            </div>
            <p className="text-xs text-text-muted">Development server. Update for production.</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileCode className="w-5 h-5 text-purple-400" />
              Interactive Docs
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <a
              href={`${baseUrl}/docs`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-3 p-3 bg-bg-elevated/50 rounded-lg border border-border/50 hover:border-primary/50 transition-colors"
            >
              <Globe className="w-5 h-5 text-text-muted" />
              <div>
                <p className="font-medium text-text">Swagger UI</p>
                <p className="text-xs text-text-muted">Interactive API documentation</p>
              </div>
              <ExternalLink className="w-4 h-4 text-text-muted ml-auto" />
            </a>
            <a
              href={`${baseUrl}/redoc`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-3 p-3 bg-bg-elevated/50 rounded-lg border border-border/50 hover:border-primary/50 transition-colors"
            >
              <FileCode className="w-5 h-5 text-text-muted" />
              <div>
                <p className="font-medium text-text">ReDoc</p>
                <p className="text-xs text-text-muted">Alternative API documentation</p>
              </div>
              <ExternalLink className="w-4 h-4 text-text-muted ml-auto" />
            </a>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Terminal className="w-5 h-5 text-amber-400" />
              Quick Test
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="p-3 bg-bg-elevated/50 rounded-lg border border-border/50">
              <p className="text-xs text-text-muted mb-2">Health check</p>
              <code className="font-mono text-sm text-text block mb-2">curl {baseUrl}/api/health</code>
              <button
                onClick={() => copyToClipboard(`curl ${baseUrl}/api/health`)}
                className="text-xs text-primary hover:underline"
              >
                Copy command
              </button>
            </div>
            <div className="p-3 bg-bg-elevated/50 rounded-lg border border-border/50">
              <p className="text-xs text-text-muted mb-2">Dashboard summary</p>
              <code className="font-mono text-sm text-text block mb-2">curl {baseUrl}/api/dashboard/summary</code>
              <button
                onClick={() => copyToClipboard(`curl ${baseUrl}/api/dashboard/summary`)}
                className="text-xs text-primary hover:underline"
              >
                Copy command
              </button>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>API Endpoints</CardTitle>
          <CardDescription>Complete list of available REST endpoints</CardDescription>
        </CardHeader>
        <CardContent>
          <Table
            data={ENDPOINTS}
            columns={[
              { key: 'method', header: 'Method', render: (row) => (
                <Badge
                  className={cn('font-mono text-xs px-2 py-0.5', METHOD_COLORS[row.method] || 'bg-bg-elevated text-text-muted border-border')}
                >
                  {row.method}
                </Badge>
              ), className: 'w-20' },
              { key: 'path', header: 'Endpoint', render: (row) => (
                <code className="font-mono text-sm text-text">{row.path}</code>
              ), className: 'w-80' },
              { key: 'description', header: 'Description', render: (row) => row.description },
              { key: 'tags', header: 'Tags', render: (row) => (
                <div className="flex flex-wrap gap-1">
                  {row.tags.map((tag: string) => (
                    <Badge key={tag} variant="neutral" className="text-[10px] px-2 py-0.5">{tag}</Badge>
                  ))}
                </div>
              ) },
              { key: 'curl', header: 'Test', render: (row) => (
                <button
                  onClick={() => copyToClipboard(`curl -X ${row.method} ${baseUrl}/api${row.path.replace(':id', '1').replace(':key', 'idem_test').replace(':ref', 'REF123')}`)}
                  className="p-1.5 text-text-muted hover:text-primary transition-colors"
                  title="Copy curl command"
                >
                  <Copy className="w-4 h-4" />
                </button>
              ), className: 'w-12' },
            ]}
            keyField="path"
            emptyMessage="No endpoints defined"
          />
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Database className="w-5 h-5" />
              Database Schema
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="p-4 bg-bg-elevated/50 rounded-lg border border-border/50">
              <h4 className="font-medium text-text mb-2">Core Tables</h4>
              <div className="space-y-1 text-sm">
                <code className="font-mono text-text block">users</code>
                <code className="font-mono text-text block">accounts</code>
                <code className="font-mono text-text block">transactions</code>
                <code className="font-mono text-text block">payment_transactions</code>
                <code className="font-mono text-text block">ledger_entries</code>
              </div>
            </div>
            <div className="p-4 bg-bg-elevated/50 rounded-lg border border-border/50">
              <h4 className="font-medium text-text mb-2">Key Relationships</h4>
              <ul className="space-y-1 text-sm text-text-muted">
                <li>User → Accounts (One-to-Many)</li>
                <li>User → Transactions (One-to-Many)</li>
                <li>Account → Payment Transactions (Sender/Receiver)</li>
                <li>Payment Transaction → Ledger Entries (One-to-Many)</li>
              </ul>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="w-5 h-5" />
              Security Notes
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="p-4 bg-bg-elevated/50 rounded-lg border border-border/50">
              <h4 className="font-medium text-text mb-2">Authentication</h4>
              <p className="text-sm text-text-muted">Currently no authentication required for development. Production deployment should implement proper auth (JWT, API keys, OAuth2).</p>
            </div>
            <div className="p-4 bg-bg-elevated/50 rounded-lg border border-border/50">
              <h4 className="font-medium text-text mb-2">Rate Limiting</h4>
              <p className="text-sm text-text-muted">Not implemented in development. Add rate limiting middleware for production.</p>
            </div>
            <div className="p-4 bg-bg-elevated/50 rounded-lg border border-border/50">
              <h4 className="font-medium text-text mb-2">CORS</h4>
              <p className="text-sm text-text-muted">Configured for localhost:5173, 127.0.0.1:5173, localhost:3000. Update for production domains.</p>
            </div>
            <div className="p-4 bg-bg-elevated/50 rounded-lg border border-border/50">
              <h4 className="font-medium text-text mb-2">Idempotency</h4>
              <p className="text-sm text-text-muted">Payment simulation requires idempotency_key. Duplicate keys return existing transaction (HTTP 409).</p>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Code className="w-5 h-5" />
            Example: Simulate Payment
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="p-4 bg-bg-elevated/50 rounded-lg border border-border/50 overflow-x-auto">
            <pre className="text-sm text-text"><code>{`curl -X POST http://localhost:8000/api/payments/simulate \\
  -H "Content-Type: application/json" \\
  -d '{
    "sender_account_id": 1,
    "receiver_account_id": 2,
    "amount": 50000,
    "payment_method": "upi_simulated",
    "idempotency_key": "idem_1234567890_abcdef"
  }'`}</code></pre>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function cn(...inputs: (string | Record<string, boolean> | undefined)[]) {
  return inputs.filter(Boolean).join(' ');
}