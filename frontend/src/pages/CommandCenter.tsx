import * as React from 'react';
import { useDashboardSummary, useLiveRiskFeed, useRecentTransactions } from '@/api';
import { formatCurrency, formatRelativeTime } from '@/utils';
import { cn } from '@/utils';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Table, Column } from '@/components/ui/Table';
import {
  Users,
  DollarSign,
  AlertTriangle,
  CheckCircle,
  TrendingUp,
  ArrowUpRight,
  ArrowDownRight,
  ExternalLink,
} from 'lucide-react';

interface LiveRiskEvent {
  id: number;
  user_id: number;
  user_name: string;
  amount: number;
  risk_level: string;
  source: string;
  timestamp: string;
  reason: string;
}

interface RecentTransaction {
  id: number;
  user_id: number;
  amount: number;
  type: string;
  status: string;
  merchant: string | null;
  category: string | null;
  city: string | null;
  timestamp: string;
  is_anomaly: boolean;
}

interface DashboardSummary {
  total_users: number;
  total_transactions: number;
  active_risk_events: number;
  system_health: string;
  trust_distribution: Record<string, number>;
  recent_transactions_count: number;
}

export function CommandCenter() {
  const { data: summary, isLoading: summaryLoading } = useDashboardSummary();
  const { data: riskFeed, isLoading: riskLoading } = useLiveRiskFeed(5);
  const { data: recentTxns, isLoading: txnsLoading } = useRecentTransactions(10);

  const statCards = [
    { name: 'Trusted Identities', value: summary?.total_users ?? 0, icon: Users, trend: '+12%', trendUp: true, color: 'text-blue-400', bgColor: 'bg-blue-500/10' },
    { name: 'Total Transactions', value: summary?.total_transactions ?? 0, icon: DollarSign, trend: '+8.2%', trendUp: true, color: 'text-emerald-400', bgColor: 'bg-emerald-500/10' },
    { name: 'Active Risk Events', value: summary?.active_risk_events ?? 0, icon: AlertTriangle, trend: '3 new', trendUp: false, color: 'text-amber-400', bgColor: 'bg-amber-500/10' },
    { name: 'System Health', value: 'Healthy', icon: CheckCircle, trend: '99.9% uptime', trendUp: true, color: 'text-emerald-400', bgColor: 'bg-emerald-500/10', isText: true },
  ];

  const riskFeedItems = React.useMemo(() => {
    if (riskLoading) {
      return [1, 2, 3].map((i) => (
        <div key={i} className="h-16 animate-pulse bg-bg-elevated rounded" />
      ));
    }
    return riskFeed?.events.slice(0, 5).map((event) => (
      <div key={event.id} className="flex items-center gap-3 p-3 bg-bg-elevated/50 rounded-lg border border-border/50">
        <div className="w-2 h-2 rounded-full bg-red-400" />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-text truncate">{event.user_name}</p>
          <p className="text-xs text-text-muted truncate">{event.reason}</p>
        </div>
        <div className="text-right">
          <Badge variant="danger" className="text-xs">HIGH</Badge>
          <p className="text-[10px] text-text-muted mt-0.5">{formatRelativeTime(event.timestamp)}</p>
        </div>
      </div>
    ));
  }, [riskFeed, riskLoading]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-text">Command Center</h1>
          <p className="text-text-muted mt-1">Trust & Risk Intelligence Platform — Real-time oversight</p>
        </div>
        <Badge variant="success" className="gap-1">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
          </span>
          System Operational
        </Badge>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((stat) => (
          <Card key={stat.name} className="relative overflow-hidden">
            <CardContent className="p-5">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-sm font-medium text-text-muted">{stat.name}</p>
                  <div className="mt-2 flex items-baseline gap-2">
                    {stat.isText ? (
                      <span className="text-2xl font-bold text-text">{stat.value}</span>
                    ) : (
                      <span className="text-3xl font-bold text-text">{stat.value.toLocaleString()}</span>
                    )}
                    <div className={cn('flex items-center gap-1 text-xs font-medium', stat.trendUp ? 'text-emerald-400' : 'text-amber-400')}>
                      {stat.trendUp ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                      <span>{stat.trend}</span>
                    </div>
                  </div>
                </div>
                <div className={cn('p-3 rounded-xl', stat.bgColor)}>
                  <CheckCircle className={cn('w-6 h-6', stat.color)} />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2">
          <CardHeader><CardTitle>Risk Activity (7 Days)</CardTitle></CardHeader>
          <CardContent>
            <div className="h-64 flex items-end justify-around gap-2 px-2">
              {[
                { day: 'Mon', events: 3 }, { day: 'Tue', events: 1 }, { day: 'Wed', events: 0 },
                { day: 'Thu', events: 2 }, { day: 'Fri', events: 4 }, { day: 'Sat', events: 1 }, { day: 'Sun', events: 0 },
              ].map((d) => (
                <div key={d.day} className="flex-1 flex flex-col items-center justify-end gap-1.5">
                  <div className="w-full bg-amber-500/60 rounded-t transition-all hover:bg-amber-500" style={{ height: `${Math.max(20, (d.events / 4) * 100)}%`, minHeight: d.events > 0 ? '24px' : '8px' }} />
                  <span className="text-xs font-medium text-text">{d.events}</span>
                  <span className="text-[10px] text-text-muted">{d.day}</span>
                </div>
              ))}
            </div>
            <div className="mt-4 flex items-center justify-between text-sm text-text-muted">
              <span>Risk Events (Amber)</span>
              <span>Transactions (Gray)</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Live Risk Feed</CardTitle>
            <Badge variant="info">Live</Badge>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {riskFeedItems}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Recent Transactions</CardTitle>
        </CardHeader>
        <CardContent>
          <Table
            data={recentTxns?.transactions ?? []}
            columns={[
              { key: 'time', header: 'Time', render: (row) => formatRelativeTime(row.timestamp) },
              { key: 'type', header: 'Type', render: (row) => <Badge variant={row.type === 'debit' ? 'info' : 'success'}>{row.type.toUpperCase()}</Badge> },
              { key: 'amount', header: 'Amount', render: (row) => formatCurrency(row.amount) },
              { key: 'merchant', header: 'Merchant', render: (row) => row.merchant ?? '—' },
              { key: 'status', header: 'Status', render: (row) => <Badge variant={row.status === 'success' ? 'success' : 'danger'}>{row.status}</Badge> },
              { key: 'risk', header: 'Risk', render: (row) => <Badge variant={row.is_anomaly ? 'danger' : 'success'}>{row.is_anomaly ? 'Anomaly' : 'Normal'}</Badge> },
            ]}
            keyField="id"
            emptyMessage="No recent transactions"
          />
        </CardContent>
      </Card>
    </div>
  );
}