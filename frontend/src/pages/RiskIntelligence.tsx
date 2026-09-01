import * as React from 'react';
import { Link } from 'react-router-dom';
import { useRiskEvents, useModelEvaluation, useRuleVsMLComparison } from '@/api';
import { formatCurrency, formatRelativeTime, getRiskLevelColor, getRiskLevelLabel } from '@/utils';
import { cn } from '@/utils';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Table, Column } from '@/components/ui/Table';
import { AlertTriangle, Search, FlaskConical, RefreshCw, Filter } from 'lucide-react';

export function RiskIntelligence() {
  const [riskLevel, setRiskLevel] = React.useState<string | undefined>();
  const [source, setSource] = React.useState<string | undefined>();
  const { data: eventsData, isLoading: eventsLoading, refetch } = useRiskEvents(100, riskLevel, source);
  const { data: evaluation, isLoading: evalLoading } = useModelEvaluation();
  const { data: comparison, isLoading: compLoading } = useRuleVsMLComparison();

  const events = eventsData?.events ?? [];

  const riskLevelOptions = [
    { value: '', label: 'All Levels' },
    { value: 'high', label: 'HIGH' },
    { value: 'moderate', label: 'MODERATE' },
    { value: 'low', label: 'LOW' },
  ];

  const sourceOptions = [
    { value: '', label: 'All Sources' },
    { value: 'rule', label: 'Rule-Based' },
    { value: 'ml', label: 'ML Anomaly' },
    { value: 'both', label: 'Both' },
  ];

  if (eventsLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold text-text">Risk Intelligence</h1>
          <p className="text-text-muted mt-1">Monitor and investigate risk events across rule-based and ML detection</p>
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

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-text">Risk Intelligence</h1>
          <p className="text-text-muted mt-1">Monitor and investigate risk events across rule-based and ML detection</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative">
            <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
            <select
              value={riskLevel || ''}
              onChange={(e) => setRiskLevel(e.target.value || undefined)}
              className="input pl-10 pr-8 w-40"
            >
              {riskLevelOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
          <div className="relative">
            <select
              value={source || ''}
              onChange={(e) => setSource(e.target.value || undefined)}
              className="input pl-10 pr-8 w-40"
            >
              {sourceOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
          <button onClick={() => refetch()} className="btn btn-secondary gap-2" disabled={eventsLoading}>
            <RefreshCw className={cn('w-4 h-4', eventsLoading && 'animate-spin')} />
            Refresh
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="p-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm font-medium text-text-muted">Total Risk Events</p>
                <p className="text-3xl font-bold text-text mt-1">{eventsData?.total ?? events.length}</p>
              </div>
              <div className="p-3 rounded-xl bg-amber-500/10">
                <AlertTriangle className="w-6 h-6 text-amber-400" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm font-medium text-text-muted">ML Anomalies Detected</p>
                <p className="text-3xl font-bold text-text mt-1">
                  {evaluation?.evaluation?.anomalies_detected ?? '—'}
                </p>
              </div>
              <div className="p-3 rounded-xl bg-blue-500/10">
                <FlaskConical className="w-6 h-6 text-blue-400" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm font-medium text-text-muted">Model F1 Score</p>
                <p className="text-3xl font-bold text-text mt-1">
                  {(evaluation?.evaluation?.f1 ? (evaluation.evaluation.f1 * 100).toFixed(1) : '—') + '%'}
                </p>
              </div>
              <div className="p-3 rounded-xl bg-emerald-500/10">
                <Search className="w-6 h-6 text-emerald-400" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Risk Events</CardTitle>
            <Badge variant="info">{events.length} showing</Badge>
          </CardHeader>
          <CardContent>
            <Table
              data={events}
              columns={[
                { key: 'time', header: 'Time', render: (row) => formatRelativeTime(row.timestamp), className: 'w-28' },
                { key: 'user', header: 'User', render: (row) => (
                  <Link to={`/trust/${row.user_id}`} className="font-medium text-text hover:text-primary">
                    {row.user_name}
                  </Link>
                )},
                { key: 'amount', header: 'Amount', render: (row) => formatCurrency(row.amount), className: 'w-32' },
                { key: 'type', header: 'Type', render: (row) => <Badge variant="info">{row.transaction_type.toUpperCase()}</Badge>, className: 'w-24' },
                { key: 'risk', header: 'Risk', render: (row) => (
                  <Badge className={getRiskLevelColor(row.risk_level)}>{getRiskLevelLabel(row.risk_level)}</Badge>
                ), className: 'w-28' },
                { key: 'source', header: 'Source', render: (row) => (
                  <Badge variant={row.rule_result && row.ml_result ? 'warning' : row.rule_result ? 'info' : 'neutral'}>
                    {row.rule_result && row.ml_result ? 'Both' : row.rule_result ? 'Rule' : 'ML'}
                  </Badge>
                ), className: 'w-24' },
                { key: 'action', header: '', render: (row) => (
                  <Link to={`/investigations/${row.id}`} className="text-primary hover:underline text-sm">
                    Investigate
                  </Link>
                ), className: 'w-28' },
              ]}
              keyField="id"
              emptyMessage="No risk events found"
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>Model Performance</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {evaluation ? (
              <>
                <div className="grid grid-cols-3 gap-4 text-center">
                  <div className="p-4 bg-bg-elevated/50 rounded-lg border border-border/50">
                    <p className="text-2xl font-bold text-text">{(evaluation.evaluation.precision * 100).toFixed(1)}%</p>
                    <p className="text-xs text-text-muted">Precision</p>
                  </div>
                  <div className="p-4 bg-bg-elevated/50 rounded-lg border border-border/50">
                    <p className="text-2xl font-bold text-text">{(evaluation.evaluation.recall * 100).toFixed(1)}%</p>
                    <p className="text-xs text-text-muted">Recall</p>
                  </div>
                  <div className="p-4 bg-bg-elevated/50 rounded-lg border border-border/50">
                    <p className="text-2xl font-bold text-text">{(evaluation.evaluation.f1 * 100).toFixed(1)}%</p>
                    <p className="text-xs text-text-muted">F1 Score</p>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4 text-center">
                  <div className="p-4 bg-bg-elevated/50 rounded-lg border border-border/50">
                    <p className="text-xl font-bold text-text">{evaluation.evaluation.anomalies_detected}</p>
                    <p className="text-xs text-text-muted">Anomalies Detected</p>
                  </div>
                  <div className="p-4 bg-bg-elevated/50 rounded-lg border border-border/50">
                    <p className="text-xl font-bold text-text">{evaluation.evaluation.false_positives}</p>
                    <p className="text-xs text-text-muted">False Positives</p>
                  </div>
                </div>
                <p className="text-xs text-text-muted text-center mt-2">{evaluation.note}</p>
              </>
            ) : evalLoading ? (
              <div className="h-40 animate-pulse bg-bg-elevated/50 rounded" />
            ) : (
              <p className="text-text-muted text-center py-8">No evaluation data available</p>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Rule vs ML Comparison</CardTitle>
        </CardHeader>
        <CardContent>
          {comparison ? (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="p-4 bg-bg-elevated/50 rounded-lg border border-border/50 text-center">
                <p className="text-2xl font-bold text-text">{comparison.counts.both}</p>
                <p className="text-xs text-text-muted">Detected by Both</p>
              </div>
              <div className="p-4 bg-bg-elevated/50 rounded-lg border border-border/50 text-center">
                <p className="text-2xl font-bold text-text">{comparison.counts.rule_only}</p>
                <p className="text-xs text-text-muted">Rule Only</p>
              </div>
              <div className="p-4 bg-bg-elevated/50 rounded-lg border border-border/50 text-center">
                <p className="text-2xl font-bold text-text">{comparison.counts.ml_only}</p>
                <p className="text-xs text-text-muted">ML Only</p>
              </div>
              <div className="p-4 bg-bg-elevated/50 rounded-lg border border-border/50 text-center">
                <p className="text-2xl font-bold text-text">{comparison.counts.neither}</p>
                <p className="text-xs text-text-muted">Neither</p>
              </div>
            </div>
          ) : compLoading ? (
            <div className="h-24 animate-pulse bg-bg-elevated/50 rounded" />
          ) : (
            <p className="text-text-muted text-center py-8">No comparison data available</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}