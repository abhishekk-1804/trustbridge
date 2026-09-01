import * as React from 'react';
import { useParams, Link } from 'react-router-dom';
import { useUser, useUserTrust, useUserTransactions, useUserPayments } from '@/api';
import { formatCurrency, formatRelativeTime, getRiskLevelColor, getStatusColor } from '@/utils';
import { cn } from '@/utils';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Table, Column } from '@/components/ui/Table';
import { ArrowLeft, User, CreditCard, Activity, AlertTriangle, CheckCircle } from 'lucide-react';

export function UserProfile() {
  const { userId } = useParams<{ userId: string }>();
  const id = Number(userId);
  const { data: user, isLoading: userLoading } = useUser(id);
  const { data: trust, isLoading: trustLoading } = useUserTrust(id);
  const { data: txns, isLoading: txnsLoading } = useUserTransactions(id, 20);
  const { data: payments, isLoading: paymentsLoading } = useUserPayments(id);

  if (userLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Link to="/trust" className="p-2 text-text-muted hover:text-text transition-colors rounded-lg hover:bg-bg-elevated">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-semibold text-text">Loading...</h1>
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="animate-pulse">
              <CardContent className="h-40" />
            </Card>
          ))}
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Link to="/trust" className="p-2 text-text-muted hover:text-text transition-colors rounded-lg hover:bg-bg-elevated">
            <ArrowLeft className="w-5 h-5" />
          </Link>
        </div>
        <Card>
          <CardContent className="py-12 text-center">
            <User className="w-12 h-12 text-text-muted mx-auto mb-4" />
            <h2 className="text-lg font-medium text-text">User not found</h2>
            <p className="text-text-muted mt-2">The requested user profile does not exist.</p>
            <Link to="/trust" className="mt-4 inline-flex items-center gap-2 text-primary hover:underline">
              <ArrowLeft className="w-4 h-4" />
              Back to Trust Profiles
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  const trustScore = trust?.trust_score ?? 0;
  const trustVerdict = trust?.verdict ?? 'Unknown';
  const components = trust?.components ?? {};

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-4">
          <Link to="/trust" className="p-2 text-text-muted hover:text-text transition-colors rounded-lg hover:bg-bg-elevated">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-semibold text-text">{user.name}</h1>
            <p className="text-text-muted">{user.email} • {user.role.replace('_', ' ')}</p>
          </div>
        </div>
        <Badge variant={user.is_verified ? 'success' : 'warning'} className="gap-1">
          {user.is_verified ? <CheckCircle className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
          {user.is_verified ? 'Verified' : 'Pending Verification'}
        </Badge>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Trust Score</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-center">
              <div className="relative w-32 h-32 mx-auto mb-4">
                <svg className="w-full h-full transform -rotate-90">
                  <circle
                    cx="64"
                    cy="64"
                    r="56"
                    fill="none"
                    stroke="var(--color-border)"
                    strokeWidth="8"
                  />
                  <circle
                    cx="64"
                    cy="64"
                    r="56"
                    fill="none"
                    stroke={trustScore >= 80 ? 'var(--color-primary)' : trustScore >= 60 ? 'var(--color-warning)' : 'var(--color-danger)'}
                    strokeWidth="8"
                    strokeDasharray={2 * Math.PI * 56}
                    strokeDashoffset={2 * Math.PI * 56 * (1 - trustScore / 100)}
                    strokeLinecap="round"
                    className="transition-all duration-500"
                  />
                </svg>
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="text-3xl font-bold text-text">{trustScore}</span>
                </div>
              </div>
              <p className="text-sm font-medium text-text">{trustVerdict}</p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Accounts</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {user.accounts?.length ? (
                user.accounts.map((acc) => (
                  <div key={acc.id} className="flex items-center justify-between p-3 bg-bg-elevated/50 rounded-lg border border-border/50">
                    <div>
                      <p className="font-medium text-text">{acc.account_type}</p>
                      <p className="text-xs text-text-muted">{acc.status}</p>
                    </div>
                    <p className="font-mono text-text">{formatCurrency(acc.balance)}</p>
                  </div>
                ))
              ) : (
                <p className="text-text-muted text-center py-4">No accounts</p>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Trust Components</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {Object.entries(components).map(([key, comp]: [string, any]) => (
                <div key={key}>
                  <div className="flex items-center justify-between text-sm mb-1">
                    <span className="text-text-muted">{key.replace('_', ' ')}</span>
                    <span className="font-medium text-text">{comp.score}/100</span>
                  </div>
                  <div className="h-2 bg-bg-elevated rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary transition-all duration-500"
                      style={{ width: `${comp.score}%` }}
                    />
                  </div>
                  <p className="text-xs text-text-muted mt-1">Weight: {(comp.weight * 100).toFixed(0)}% • Contribution: {comp.contribution.toFixed(1)}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Recent Transactions</CardTitle>
            <Badge variant="info">{txns?.total ?? 0} total</Badge>
          </CardHeader>
          <CardContent>
            <Table
              data={txns?.transactions ?? []}
              columns={[
                { key: 'time', header: 'Time', render: (row) => formatRelativeTime(row.timestamp) },
                { key: 'transaction_type', header: 'Type', render: (row) => <Badge variant={row.transaction_type === 'debit' ? 'info' : 'success'}>{row.transaction_type.toUpperCase()}</Badge> },
                { key: 'amount', header: 'Amount', render: (row) => formatCurrency(row.amount) },
                { key: 'merchant_name', header: 'Merchant', render: (row) => row.merchant_name ?? '—' },
                { key: 'status', header: 'Status', render: (row) => <Badge variant={getStatusColor(row.status).includes('emerald') ? 'success' : 'danger'}>{row.status}</Badge> },
                { key: 'risk', header: 'Risk', render: (row) => <Badge variant={row.is_anomaly ? 'danger' : 'success'}>{row.is_anomaly ? 'Anomaly' : 'Normal'}</Badge> },
              ]}
              keyField="id"
              emptyMessage="No transactions found"
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Payment Activity</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {payments && (payments.sent.length > 0 || payments.received.length > 0) ? (
                <>
                  {payments.sent.length > 0 && (
                    <div>
                      <h4 className="text-sm font-medium text-text-muted mb-2">Sent</h4>
                      <div className="space-y-2 max-h-64 overflow-y-auto">
                        {payments.sent.slice(0, 10).map((p) => (
                          <div key={p.id} className="flex items-center justify-between p-3 bg-bg-elevated/50 rounded-lg border border-border/50">
                            <div className="flex items-center gap-3">
                              <CreditCard className="w-5 h-5 text-text-muted" />
                              <div>
                                <p className="font-medium text-text">{formatCurrency(p.amount)}</p>
                                <p className="text-xs text-text-muted">{p.payment_method.replace('_', ' ').toUpperCase()}</p>
                              </div>
                            </div>
                            <div className="text-right">
                              <Badge variant={p.status === 'completed' ? 'success' : p.status === 'rejected' ? 'danger' : 'warning'}>{p.status}</Badge>
                              <p className="text-[10px] text-text-muted mt-1">{formatRelativeTime(p.created_at)}</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  {payments.received.length > 0 && (
                    <div className="pt-4 border-t border-border">
                      <h4 className="text-sm font-medium text-text-muted mb-2">Received</h4>
                      <div className="space-y-2 max-h-64 overflow-y-auto">
                        {payments.received.slice(0, 10).map((p) => (
                          <div key={p.id} className="flex items-center justify-between p-3 bg-bg-elevated/50 rounded-lg border border-border/50">
                            <div className="flex items-center gap-3">
                              <Activity className="w-5 h-5 text-primary" />
                              <div>
                                <p className="font-medium text-text">{formatCurrency(p.amount)}</p>
                                <p className="text-xs text-text-muted">{p.payment_method.replace('_', ' ').toUpperCase()}</p>
                              </div>
                            </div>
                            <div className="text-right">
                              <Badge variant={p.status === 'completed' ? 'success' : 'warning'}>{p.status}</Badge>
                              <p className="text-[10px] text-text-muted mt-1">{formatRelativeTime(p.created_at)}</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <p className="text-text-muted text-center py-8">No payment activity</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}