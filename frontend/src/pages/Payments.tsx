import * as React from 'react';
import { usePayments, useSimulatePayment, useAccountPayments, useLedger, useVerifyLedger } from '@/api';
import { formatCurrency, formatRelativeTime, formatDate, generateIdempotencyKey, getStatusColor } from '@/utils';
import { cn } from '@/utils';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Table, Column } from '@/components/ui/Table';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { CreditCard, ArrowLeftRight, RefreshCw, Search, List, Hash, CheckCircle, XCircle, AlertTriangle } from 'lucide-react';

const PAYMENT_METHODS = [
  { value: 'upi_simulated', label: 'UPI (Simulated)' },
  { value: 'bank_transfer_simulated', label: 'Bank Transfer (Simulated)' },
  { value: 'wallet_simulated', label: 'Wallet (Simulated)' },
];

const STATUS_OPTIONS = [
  { value: '', label: 'All Statuses' },
  { value: 'pending', label: 'Pending' },
  { value: 'completed', label: 'Completed' },
  { value: 'failed', label: 'Failed' },
  { value: 'rejected', label: 'Rejected' },
  { value: 'reversed', label: 'Reversed' },
];

export function Payments() {
  const [statusFilter, setStatusFilter] = React.useState('');
  const [showSimulate, setShowSimulate] = React.useState(false);
  const [simForm, setSimForm] = React.useState({
    sender_account_id: '',
    receiver_account_id: '',
    amount: '',
    payment_method: 'upi_simulated',
    idempotency_key: generateIdempotencyKey(),
  });
  const [simError, setSimError] = React.useState('');
  const [simSuccess, setSimSuccess] = React.useState(false);

  const { data: paymentsData, isLoading, refetch } = usePayments(50, 0, statusFilter || undefined);
  const simulateMutation = useSimulatePayment();

  const handleSimulate = async (e: React.FormEvent) => {
    e.preventDefault();
    setSimError('');
    setSimSuccess(false);

    try {
      await simulateMutation.mutateAsync({
        sender_account_id: Number(simForm.sender_account_id),
        receiver_account_id: Number(simForm.receiver_account_id),
        amount: Number(simForm.amount),
        payment_method: simForm.payment_method as any,
        idempotency_key: simForm.idempotency_key,
      });
      setSimSuccess(true);
      setSimForm({ ...simForm, idempotency_key: generateIdempotencyKey() });
      refetch();
    } catch (err: any) {
      setSimError(err.message || 'Payment simulation failed');
    }
  };

  const payments = paymentsData ?? [];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-text">Payments</h1>
          <p className="text-text-muted mt-1">Simulate payments, view transaction history, and verify ledger integrity</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => setShowSimulate(!showSimulate)}
            className="btn btn-primary gap-2"
          >
            <ArrowLeftRight className="w-4 h-4" />
            Simulate Payment
          </button>
          <button onClick={() => refetch()} className="btn btn-secondary gap-2" disabled={isLoading}>
            <RefreshCw className={cn('w-4 h-4', isLoading && 'animate-spin')} />
            Refresh
          </button>
        </div>
      </div>

      {showSimulate && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ArrowLeftRight className="w-5 h-5" />
              Simulate Payment
            </CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSimulate} className="space-y-4 max-w-md">
              {simError && (
                <div className="p-3 bg-danger-bg border border-danger-border rounded-lg text-sm text-danger">
                  <AlertTriangle className="w-4 h-4 inline mr-1" />
                  {simError}
                </div>
              )}
              {simSuccess && (
                <div className="p-3 bg-primary-bg border border-primary-border rounded-lg text-sm text-primary">
                  <CheckCircle className="w-4 h-4 inline mr-1" />
                  Payment simulated successfully!
                </div>
              )}

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-text-muted mb-1">Sender Account ID</label>
                  <Input
                    type="number"
                    value={simForm.sender_account_id}
                    onChange={(e) => setSimForm({ ...simForm, sender_account_id: e.target.value })}
                    placeholder="e.g., 1"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-text-muted mb-1">Receiver Account ID</label>
                  <Input
                    type="number"
                    value={simForm.receiver_account_id}
                    onChange={(e) => setSimForm({ ...simForm, receiver_account_id: e.target.value })}
                    placeholder="e.g., 2"
                    required
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-text-muted mb-1">Amount (INR)</label>
                  <Input
                    type="number"
                    step="0.01"
                    min="0.01"
                    value={simForm.amount}
                    onChange={(e) => setSimForm({ ...simForm, amount: e.target.value })}
                    placeholder="e.g., 100.00"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-text-muted mb-1">Payment Method</label>
                  <Select
                    value={simForm.payment_method}
                    onChange={(e) => setSimForm({ ...simForm, payment_method: e.target.value })}
                    options={PAYMENT_METHODS}
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-text-muted mb-1">Idempotency Key</label>
                <Input
                  value={simForm.idempotency_key}
                  onChange={(e) => setSimForm({ ...simForm, idempotency_key: e.target.value })}
                  placeholder="Auto-generated or custom"
                />
                <p className="text-xs text-text-muted mt-1">Used to prevent duplicate payments. Reusing a key will return the existing transaction.</p>
              </div>

              <div className="flex gap-3 pt-2">
                <button type="submit" className="btn btn-primary gap-2 flex-1" disabled={simulateMutation.isPending}>
                  {simulateMutation.isPending ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      Processing...
                    </>
                  ) : (
                    <>
                      <ArrowLeftRight className="w-4 h-4" />
                      Simulate Payment
                    </>
                  )}
                </button>
                <button
                  type="button"
                  onClick={() => setShowSimulate(false)}
                  className="btn btn-secondary"
                >
                  Cancel
                </button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Payment Transactions</CardTitle>
          <div className="flex items-center gap-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="input pl-10 pr-8 w-40"
              >
                {STATUS_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
            </div>
            <Badge variant="info">{payments.length} transactions</Badge>
          </div>
        </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="h-64 animate-pulse bg-bg-elevated/50 rounded" />
            ) : payments.length === 0 ? (
              <div className="text-center py-12">
                <ArrowLeftRight className="w-12 h-12 text-text-muted mx-auto mb-4" />
                <h3 className="text-lg font-medium text-text">No payments found</h3>
                <p className="text-text-muted mt-2">Simulate a payment to get started</p>
              </div>
            ) : (
              <Table
                data={payments}
                columns={[
                  { key: 'time', header: 'Time', render: (row) => formatRelativeTime(row.created_at), className: 'w-28' },
                  { key: 'ref', header: 'Reference', render: (row) => (
                    <span className="font-mono text-sm text-text">{row.reference_id}</span>
                  ), className: 'w-48' },
                  { key: 'method', header: 'Method', render: (row) => (
                    <Badge variant="neutral" className="text-xs">{row.payment_method.replace('_', ' ').toUpperCase()}</Badge>
                  ), className: 'w-36' },
                  { key: 'amount', header: 'Amount', render: (row) => formatCurrency(row.amount), className: 'w-28' },
                  { key: 'status', header: 'Status', render: (row) => (
                    <Badge className={getStatusColor(row.status)}>{row.status.toUpperCase()}</Badge>
                  ), className: 'w-28' },
                  { key: 'trust', header: 'Trust', render: (row) => row.trust_score !== null ? (
                    <span className={cn('font-mono', row.trust_score >= 80 ? 'text-emerald-400' : row.trust_score >= 60 ? 'text-amber-400' : 'text-red-400')}>
                      {row.trust_score.toFixed(1)}
                    </span>
                  ) : '—', className: 'w-20' },
                  { key: 'risk', header: 'Risk Decision', render: (row) => row.risk_policy_decision ? (
                    <Badge variant={
                      row.risk_policy_decision === 'reject' ? 'danger' :
                      row.risk_policy_decision === 'flag' ? 'warning' : 'success'
                    }>{row.risk_policy_decision.toUpperCase()}</Badge>
                  ) : '—', className: 'w-32' },
                  { key: 'actions', header: '', render: (row) => (
                    <div className="flex items-center gap-2">
                      <button className="p-1.5 text-text-muted hover:text-primary transition-colors" title="View Ledger">
                        <Hash className="w-4 h-4" />
                      </button>
                      <button className="p-1.5 text-text-muted hover:text-primary transition-colors" title="Verify Ledger">
                        <CheckCircle className="w-4 h-4" />
                      </button>
                    </div>
                  ), className: 'w-24' },
                ]}
                keyField="id"
                emptyMessage="No payments found"
              />
            )}
          </CardContent>
        </Card>
      </div>
  );
}