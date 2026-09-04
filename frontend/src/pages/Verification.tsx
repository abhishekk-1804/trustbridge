import * as React from 'react';
import { useUsers } from '@/api';
import { formatCurrency, formatRelativeTime, getRiskLevelColor, getRiskLevelLabel } from '@/utils';
import { cn } from '@/utils';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Table, Column } from '@/components/ui/Table';
import { Input } from '@/components/ui/Input';
import { Shield, Search, CheckCircle, AlertTriangle, UserCheck, UserX, Clock, Eye, FileText, AlertCircle, Info } from 'lucide-react';
import { User } from '@/types';

interface VerificationUser extends User {
  verification_status: 'verified' | 'pending' | 'rejected' | 'flagged';
  verification_date: string | null;
  verification_notes: string;
  risk_flags: string[];
  trust_score?: number;
}

const VERIFICATION_STATUSES = [
  { value: 'verified', label: 'Verified', icon: CheckCircle, color: 'emerald' },
  { value: 'pending', label: 'Pending', icon: Clock, color: 'amber' },
  { value: 'rejected', label: 'Rejected', icon: AlertTriangle, color: 'red' },
  { value: 'flagged', label: 'Flagged', icon: Shield, color: 'blue' },
];

export function Verification() {
  const [search, setSearch] = React.useState('');
  const [statusFilter, setStatusFilter] = React.useState('');
  const { data: usersData, isLoading } = useUsers(200);

  const users = usersData?.users ?? [];

  const filteredUsers = users.filter((u) => {
    const matchesSearch = u.name.toLowerCase().includes(search.toLowerCase()) ||
      u.email.toLowerCase().includes(search.toLowerCase());
    const matchesStatus = !statusFilter || (u.is_verified ? 'verified' : 'pending') === statusFilter;
    return matchesSearch && matchesStatus;
  });

  // Add mock verification data since backend doesn't have it yet
  const usersWithVerification: VerificationUser[] = filteredUsers.map((u) => ({
    ...u,
    verification_status: u.is_verified ? 'verified' : 'pending',
    verification_date: u.is_verified ? u.account_created_at : null,
    verification_notes: u.is_verified ? 'KYC completed (mock)' : 'Awaiting document review (mock)',
    risk_flags: [] as string[],
    trust_score: undefined,
  }));

  return (
    <div className="space-y-6">
      {/* Demo Notice Banner */}
      <Card className="border-amber-500/30 bg-amber-500/5">
        <CardContent className="p-4 flex items-start gap-3">
          <Info className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-amber-300">Demo Only — Verification Workflow Not Implemented</p>
            <p className="text-xs text-text-muted mt-1">
              This page displays mock verification statuses derived from <code className="font-mono">is_verified</code>.
              No backend verification endpoints exist. Approve/Reject actions are disabled.
              Connect a real KYC/verification service to enable this workflow.
            </p>
          </div>
        </CardContent>
      </Card>

      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-text">Verifications</h1>
          <p className="text-text-muted mt-1">User identity verification and compliance review</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative w-full sm:w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
            <Input
              type="text"
              placeholder="Search users..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-10"
            />
          </div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="input w-40"
          >
            <option value="">All Statuses</option>
            {VERIFICATION_STATUSES.map((s) => (
              <option key={s.value} value={s.value}>{s.label}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm font-medium text-text-muted">Total Users</p>
                <p className="text-3xl font-bold text-text mt-1">{users.length}</p>
              </div>
              <div className="p-3 rounded-xl bg-blue-500/10">
                <UserCheck className="w-6 h-6 text-blue-400" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm font-medium text-text-muted">Verified</p>
                <p className="text-3xl font-bold text-emerald-400 mt-1">
                  {usersWithVerification.filter(u => u.verification_status === 'verified').length}
                </p>
              </div>
              <div className="p-3 rounded-xl bg-emerald-500/10">
                <CheckCircle className="w-6 h-6 text-emerald-400" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm font-medium text-text-muted">Pending Review</p>
                <p className="text-3xl font-bold text-amber-400 mt-1">
                  {usersWithVerification.filter(u => u.verification_status === 'pending').length}
                </p>
              </div>
              <div className="p-3 rounded-xl bg-amber-500/10">
                <Clock className="w-6 h-6 text-amber-400" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm font-medium text-text-muted">Flagged</p>
                <p className="text-3xl font-bold text-blue-400 mt-1">
                  {usersWithVerification.filter(u => u.verification_status === 'flagged').length}
                </p>
              </div>
              <div className="p-3 rounded-xl bg-blue-500/10">
                <Shield className="w-6 h-6 text-blue-400" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>User Verification Queue</CardTitle>
          <Badge variant="info">{filteredUsers.length} users</Badge>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="h-64 animate-pulse bg-bg-elevated/50 rounded" />
          ) : filteredUsers.length === 0 ? (
            <div className="text-center py-12">
              <Shield className="w-12 h-12 text-text-muted mx-auto mb-4" />
              <h3 className="text-lg font-medium text-text">No users found</h3>
              <p className="text-text-muted mt-2">Try adjusting your filters</p>
            </div>
          ) : (
            <Table
              data={usersWithVerification}
              columns={[
                { key: 'user', header: 'User', render: (row) => (
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center">
                      <span className="text-primary font-medium text-sm">
                        {row.name.charAt(0)}
                      </span>
                    </div>
                    <div>
                      <p className="font-medium text-text">{row.name}</p>
                      <p className="text-xs text-text-muted">{row.email}</p>
                    </div>
                  </div>
                )},
                { key: 'role', header: 'Role', render: (row) => (
                  <Badge variant="neutral" className="text-xs">{row.role.replace('_', ' ')}</Badge>
                ), className: 'w-36' },
                { key: 'status', header: 'Verification', render: (row) => {
                  const status = VERIFICATION_STATUSES.find(s => s.value === row.verification_status) || VERIFICATION_STATUSES[1];
                  const Icon = status.icon;
                  return (
                    <Badge variant={status.color as any} className="gap-1">
                      <Icon className="w-3 h-3" />
                      {status.label}
                    </Badge>
                  );
                }, className: 'w-36' },
                { key: 'date', header: 'Verified Date', render: (row) => (
                  row.verification_date ? formatRelativeTime(row.verification_date) : '—'
                ), className: 'w-40' },
                { key: 'trust', header: 'Trust Score', render: (row) => (
                  <span className="font-mono text-sm">
                    {row.trust_score !== undefined ? row.trust_score.toFixed(1) : '—'}
                  </span>
                ), className: 'w-28' },
                { key: 'risk', header: 'Risk Flags', render: (row) => (
                  <div className="flex flex-wrap gap-1">
                    {row.risk_flags.length > 0 ? (
                      row.risk_flags.map((flag: string, i: number) => (
                        <Badge key={i} variant="danger" className="text-[10px]">{flag}</Badge>
                      ))
                    ) : (
                      <Badge variant="success" className="text-[10px]">Clean</Badge>
                    )}
                  </div>
                )},
                { key: 'notes', header: 'Notes', render: (row) => (
                  <span className="text-sm text-text-muted max-w-xs truncate block">{row.verification_notes}</span>
                )},
                { key: 'actions', header: 'Actions', render: (row) => (
                  <div className="flex items-center gap-1">
                    <button className="p-1.5 text-text-muted hover:text-primary transition-colors" title="View Details (demo)">
                      <Eye className="w-4 h-4" />
                    </button>
                    <button className="p-1.5 text-text-muted hover:text-primary transition-colors" title="View Documents (demo)">
                      <FileText className="w-4 h-4" />
                    </button>
                    {row.verification_status === 'pending' && (
                      <>
                        <button
                          className="p-1.5 text-emerald-400 hover:bg-emerald-500/10 rounded transition-colors opacity-50 cursor-not-allowed"
                          title="Approve — Not implemented (no backend endpoint)"
                          disabled
                          aria-disabled="true"
                        >
                          <CheckCircle className="w-4 h-4" />
                        </button>
                        <button
                          className="p-1.5 text-red-400 hover:bg-red-500/10 rounded transition-colors opacity-50 cursor-not-allowed"
                          title="Reject — Not implemented (no backend endpoint)"
                          disabled
                          aria-disabled="true"
                        >
                          <UserX className="w-4 h-4" />
                        </button>
                      </>
                    )}
                  </div>
                ), className: 'w-40' },
              ]}
              keyField="id"
              emptyMessage="No users match the current filters"
            />
          )}
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="w-5 h-5" />
              Required Documents
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="p-3 bg-bg-elevated/50 rounded-lg border border-border/50">
              <div className="flex items-center gap-3">
                <CheckCircle className="w-5 h-5 text-emerald-400" />
                <div>
                  <p className="font-medium text-text">Government ID</p>
                  <p className="text-xs text-text-muted">Aadhaar, PAN, Passport, or Driver's License</p>
                </div>
              </div>
            </div>
            <div className="p-3 bg-bg-elevated/50 rounded-lg border border-border/50">
              <div className="flex items-center gap-3">
                <CheckCircle className="w-5 h-5 text-emerald-400" />
                <div>
                  <p className="font-medium text-text">Address Proof</p>
                  <p className="text-xs text-text-muted">Utility bill, bank statement, or rental agreement</p>
                </div>
              </div>
            </div>
            <div className="p-3 bg-bg-elevated/50 rounded-lg border border-border/50">
              <div className="flex items-center gap-3">
                <CheckCircle className="w-5 h-5 text-emerald-400" />
                <div>
                  <p className="font-medium text-text">Selfie Verification</p>
                  <p className="text-xs text-text-muted">Live selfie for liveness check</p>
                </div>
              </div>
            </div>
            <div className="p-3 bg-bg-elevated/50 rounded-lg border border-border/50">
              <div className="flex items-center gap-3">
                <AlertTriangle className="w-5 h-5 text-amber-400" />
                <div>
                  <p className="font-medium text-text">Source of Funds (High Value)</p>
                  <p className="text-xs text-text-muted">Required for transactions {'>'} ₹50,000</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="w-5 h-5" />
              Compliance Rules
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="p-3 bg-bg-elevated/50 rounded-lg border border-border/50">
              <p className="font-medium text-text mb-1">KYC Threshold</p>
              <p className="text-sm text-text-muted">Full KYC required for accounts with {'>'} ₹1,00,000 balance or {'>'} ₹50,000 single transaction</p>
            </div>
            <div className="p-3 bg-bg-elevated/50 rounded-lg border border-border/50">
              <p className="font-medium text-text mb-1">PEP Screening</p>
              <p className="text-sm text-text-muted">Politically Exposed Persons screening on onboarding and quarterly</p>
            </div>
            <div className="p-3 bg-bg-elevated/50 rounded-lg border border-border/50">
              <p className="font-medium text-text mb-1">Sanctions Check</p>
              <p className="text-sm text-text-muted">Real-time screening against UN, OFAC, EU sanctions lists</p>
            </div>
            <div className="p-3 bg-bg-elevated/50 rounded-lg border border-border/50">
              <p className="font-medium text-text mb-1">Adverse Media</p>
              <p className="text-sm text-text-muted">Negative news monitoring for high-risk users</p>
            </div>
            <div className="p-3 bg-bg-elevated/50 rounded-lg border border-border/50">
              <p className="font-medium text-text mb-1">Ongoing Monitoring</p>
              <p className="text-sm text-text-muted">Transaction monitoring with rule-based and ML anomaly detection</p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
