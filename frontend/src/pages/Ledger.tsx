import * as React from 'react';
import { useParams, Link } from 'react-router-dom';
import { useLedger, useVerifyLedger, usePayment } from '@/api';
import { formatCurrency, formatRelativeTime } from '@/utils';
import { cn } from '@/utils';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Table } from '@/components/ui/Table';
import { ArrowLeft, List, CheckCircle, AlertTriangle, RefreshCw, XCircle, Hash } from 'lucide-react';

export function Ledger() {
  const { paymentId } = useParams<{ paymentId: string }>();
  const id = Number(paymentId);
  const { data: payment, isLoading: paymentLoading, error: paymentError } = usePayment(id);
  const { data: ledgerData, isLoading: ledgerLoading, error: ledgerError } = useLedger(id);
  const verifyMutation = useVerifyLedger(id);
  const [verifyResult, setVerifyResult] = React.useState<any>(null);

  const handleVerify = async () => {
    try {
      const result = await verifyMutation.mutateAsync();
      setVerifyResult(result);
    } catch (err: any) {
      setVerifyResult({ error: err.message || 'Verification failed' });
    }
  };

  if (paymentLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Link to="/payments" className="p-2 text-text-muted hover:text-text transition-colors rounded-lg hover:bg-bg-elevated">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-semibold text-text">Loading...</h1>
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[1, 2].map((i) => (
            <Card key={i} className="animate-pulse">
              <CardContent className="h-64" />
            </Card>
          ))}
        </div>
      </div>
    );
  }

  if (paymentError || !payment) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Link to="/payments" className="p-2 text-text-muted hover:text-text transition-colors rounded-lg hover:bg-bg-elevated">
            <ArrowLeft className="w-5 h-5" />
          </Link>
        </div>
        <Card>
          <CardContent className="py-12 text-center">
            <AlertTriangle className="w-12 h-12 text-text-muted mx-auto mb-4" />
            <h2 className="text-lg font-medium text-text">Payment Not Found</h2>
            <p className="text-text-muted mt-2">The requested payment could not be found.</p>
            <Link to="/payments" className="mt-4 inline-flex items-center gap-2 text-primary hover:underline">
              <ArrowLeft className="w-4 h-4" />
              Back to Payments
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-4">
          <Link to="/payments" className="p-2 text-text-muted hover:text-text transition-colors rounded-lg hover:bg-bg-elevated">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-semibold text-text">Ledger</h1>
            <p className="text-text-muted">Payment #{payment.id} — {payment.reference_id}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Badge variant="info">{payment.payment_method.replace('_', ' ').toUpperCase()}</Badge>
          <Badge className={cn('gap-1', payment.status === 'completed' ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20' : payment.status === 'rejected' ? 'text-red-400 bg-red-500/10 border-red-500/20' : 'text-amber-400 bg-amber-500/10 border-amber-500/20')}>
            {payment.status.toUpperCase()}
          </Badge>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <Hash className="w-5 h-5" />
                Ledger Entries
              </CardTitle>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleVerify}
                  disabled={verifyMutation.isPending}
                  className="btn btn-secondary gap-2"
                >
                  <CheckCircle className="w-4 h-4" />
                  Verify Ledger
                </button>
              </div>
            </CardHeader>
            <CardContent>
              {ledgerLoading ? (
                <div className="h-64 animate-pulse bg-bg-elevated/50 rounded" />
              ) : ledgerError ? (
                <div className="p-4 text-text-danger text-sm">Failed to load ledger entries</div>
              ) : ledgerData && ledgerData.length > 0 ? (
                <>
                  <Table
                    data={ledgerData}
                    columns={[
                      { key: 'entry_type', header: 'Type', render: (row) => (
                        <Badge variant={row.entry_type === 'debit' ? 'info' : 'success'}>{row.entry_type.toUpperCase()}</Badge>
                      ), className: 'w-24' },
                      { key: 'account_id', header: 'Account', render: (row) => <span className="font-mono text-sm">#{row.account_id}</span>, className: 'w-24' },
                      { key: 'amount', header: 'Amount', render: (row) => formatCurrency(row.amount), className: 'w-28' },
                      { key: 'balance_after', header: 'Balance After', render: (row) => formatCurrency(row.balance_after), className: 'w-32' },
                      { key: 'description', header: 'Description', render: (row) => row.description ?? '—', className: 'w-48' },
                      { key: 'created_at', header: 'Time', render: (row) => formatRelativeTime(row.created_at), className: 'w-36' },
                    ]}
                    keyField="id"
                    emptyMessage="No ledger entries found"
                  />
                  <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
                    <div className="p-3 bg-bg-elevated/50 rounded-lg border border-border/50">
                      <p className="text-text-muted">Total Debits</p>
                      <p className="font-mono text-text">
                        {formatCurrency(ledgerData.filter(e => e.entry_type === 'debit').reduce((sum, e) => sum + e.amount, 0))}
                      </p>
                    </div>
                    <div className="p-3 bg-bg-elevated/50 rounded-lg border border-border/50">
                      <p className="text-text-muted">Total Credits</p>
                      <p className="font-mono text-text">
                        {formatCurrency(ledgerData.filter(e => e.entry_type === 'credit').reduce((sum, e) => sum + e.amount, 0))}
                      </p>
                    </div>
                  </div>
                </>
              ) : (
                <div className="text-center py-12">
                  <List className="w-12 h-12 text-text-muted mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-text">No ledger entries</h3>
                  <p className="text-text-muted mt-2">This payment has no ledger entries</p>
                </div>
              )}
            </CardContent>
          </Card>

          {verifyResult && (
            <Card className={verifyResult.error ? 'border-danger-border/50' : 'border-primary-border/50'}>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <CheckCircle className={cn('w-5 h-5', verifyResult.error ? 'text-red-400' : 'text-emerald-400')} />
                  Verification Result
                </CardTitle>
                <button
                  onClick={() => setVerifyResult(null)}
                  className="p-1.5 text-text-muted hover:text-text transition-colors"
                  title="Dismiss"
                >
                  <XCircle className="w-4 h-4" />
                </button>
              </CardHeader>
              <CardContent>
                {verifyResult.error ? (
                  <div className="p-4 bg-danger-bg border border-danger-border rounded-lg">
                    <p className="text-sm text-danger flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4" />
                      {verifyResult.error}
                    </p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div className="p-4 bg-primary-bg border border-primary-border rounded-lg">
                      <div className="flex items-center gap-2 mb-3">
                        <CheckCircle className="w-5 h-5 text-primary" />
                        <h3 className="text-lg font-medium text-text">Ledger Verified</h3>
                      </div>
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <p className="text-text-muted">Balanced</p>
                          <p className="font-mono text-text">{verifyResult.is_balanced ? 'Yes' : 'No'}</p>
                        </div>
                        <div>
                          <p className="text-text-muted">Total Debits</p>
                          <p className="font-mono text-text">{formatCurrency(verifyResult.total_debits)}</p>
                        </div>
                        <div>
                          <p className="text-text-muted">Total Credits</p>
                          <p className="font-mono text-text">{formatCurrency(verifyResult.total_credits)}</p>
                        </div>
                        <div>
                          <p className="text-text-muted">Entry Count</p>
                          <p className="font-mono text-text">{verifyResult.entry_count}</p>
                        </div>
                      </div>
                    </div>
                    {verifyResult.entries && verifyResult.entries.length > 0 && (
                      <div className="pt-4 border-t border-border">
                        <h4 className="text-sm font-medium text-text-muted mb-2">Entries</h4>
                        <Table
                          data={verifyResult.entries}
                          columns={[
                            { key: 'account_id', header: 'Account', render: (row) => <span className="font-mono text-sm">#{row.account_id}</span> },
                            { key: 'entry_type', header: 'Type', render: (row) => (
                              <Badge variant={row.entry_type === 'debit' ? 'info' : 'success'}>{row.entry_type.toUpperCase()}</Badge>
                            ) },
                            { key: 'amount', header: 'Amount', render: (row) => formatCurrency(row.amount) },
                            { key: 'balance_after', header: 'Balance After', render: (row) => formatCurrency(row.balance_after) },
                          ]}
                          keyField="account_id"
                          emptyMessage="No entries"
                        />
                      </div>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Hash className="w-5 h-5" />
                Payment Summary
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="p-3 bg-bg-elevated/50 rounded-lg border border-border/50">
                <p className="text-xs text-text-muted">Reference ID</p>
                <p className="font-mono text-sm text-text break-all">{payment.reference_id}</p>
              </div>
              <div className="p-3 bg-bg-elevated/50 rounded-lg border border-border/50">
                <p className="text-xs text-text-muted">Amount</p>
                <p className="font-mono text-xl text-text">{formatCurrency(payment.amount)}</p>
              </div>
              <div className="p-3 bg-bg-elevated/50 rounded-lg border border-border/50">
                <p className="text-xs text-text-muted">Payment Method</p>
                <p className="text-sm text-text capitalize">{payment.payment_method.replace('_', ' ')}</p>
              </div>
              <div className="p-3 bg-bg-elevated/50 rounded-lg border border-border/50">
                <p className="text-xs text-text-muted">Status</p>
                <Badge className={cn(payment.status === 'completed' ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20' : payment.status === 'rejected' ? 'text-red-400 bg-red-500/10 border-red-500/20' : 'text-amber-400 bg-amber-500/10 border-amber-500/20')}>
                  {payment.status.toUpperCase()}
                </Badge>
              </div>
              {payment.trust_score !== null && payment.trust_score !== undefined && (
                <div className="p-3 bg-bg-elevated/50 rounded-lg border border-border/50">
                  <p className="text-xs text-text-muted">Trust Score at Payment</p>
                  <p className="text-2xl font-bold text-text">{payment.trust_score.toFixed(1)}</p>
                </div>
              )}
              {payment.risk_policy_decision && (
                <div className="p-3 bg-bg-elevated/50 rounded-lg border border-border/50">
                  <p className="text-xs text-text-muted">Risk Decision</p>
                  <Badge variant={
                    payment.risk_policy_decision === 'reject' ? 'danger' :
                    payment.risk_policy_decision === 'flag' ? 'warning' : 'success'
                  }>{payment.risk_policy_decision.toUpperCase()}</Badge>
                </div>
              )}
              <div className="p-3 bg-bg-elevated/50 rounded-lg border border-border/50">
                <p className="text-xs text-text-muted">Created</p>
                <p className="text-sm text-text">{formatRelativeTime(payment.created_at)}</p>
              </div>
              {payment.completed_at && (
                <div className="p-3 bg-bg-elevated/50 rounded-lg border border-border/50">
                  <p className="text-xs text-text-muted">Completed</p>
                  <p className="text-sm text-text">{formatRelativeTime(payment.completed_at)}</p>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Hash className="w-5 h-5" />
                Ledger Integrity
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="p-3 bg-bg-elevated/50 rounded-lg border border-border/50">
                <p className="text-xs text-text-muted">Double-Entry Bookkeeping</p>
                <p className="text-sm text-text mt-1">Every payment creates balanced debit and credit entries across sender and receiver accounts.</p>
              </div>
              <div className="p-3 bg-bg-elevated/50 rounded-lg border border-border/50">
                <p className="text-xs text-text-muted">Idempotency Protection</p>
                <p className="text-sm text-text mt-1">Duplicate payments with the same idempotency key return the existing transaction (HTTP 409).</p>
              </div>
              <div className="p-3 bg-bg-elevated/50 rounded-lg border border-border/50">
                <p className="text-xs text-text-muted">Verification</p>
                <p className="text-sm text-text mt-1">Click "Verify Ledger" to confirm all entries balance correctly for this payment.</p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}