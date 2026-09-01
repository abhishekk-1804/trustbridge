import * as React from 'react';
import { useModelEvaluation, useRuleVsMLComparison, useRiskEvents } from '@/api';
import { formatCurrency, getRiskLevelColor, getRiskLevelLabel } from '@/utils';
import { cn } from '@/utils';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Table, Column } from '@/components/ui/Table';
import { RefreshCw, FlaskConical, BarChart2, Target, AlertTriangle, CheckCircle, XCircle, Search, Brain, Shield } from 'lucide-react';

export function ModelLab() {
  const { data: evaluation, isLoading: evalLoading, refetch: refetchEval } = useModelEvaluation();
  const { data: comparison, isLoading: compLoading } = useRuleVsMLComparison();
  const { data: eventsData, isLoading: eventsLoading } = useRiskEvents(200);

  const events = eventsData?.events ?? [];
  const mlEvents = events.filter(e => e.ml_result?.is_anomaly);
  const ruleEvents = events.filter(e => e.rule_result?.flagged);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-text">Model Lab</h1>
          <p className="text-text-muted mt-1">ML model evaluation, rule vs ML comparison, and anomaly analysis</p>
        </div>
        <div className="flex gap-3">
          <button onClick={() => refetchEval()} className="btn btn-secondary gap-2" disabled={evalLoading}>
            <RefreshCw className={cn('w-4 h-4', evalLoading && 'animate-spin')} />
            Refresh Evaluation
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="p-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm font-medium text-text-muted">Model</p>
                <p className="text-lg font-bold text-text mt-1">Isolation Forest v1.0</p>
              </div>
              <div className="p-3 rounded-xl bg-purple-500/10">
                <Brain className="w-6 h-6 text-purple-400" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm font-medium text-text-muted">Training Data</p>
                <p className="text-lg font-bold text-text mt-1">{evaluation?.evaluation?.total_transactions ?? '—'} transactions</p>
              </div>
              <div className="p-3 rounded-xl bg-blue-500/10">
                <BarChart2 className="w-6 h-6 text-blue-400" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm font-medium text-text-muted">Injected Anomalies</p>
                <p className="text-lg font-bold text-text mt-1">{evaluation?.evaluation?.true_anomalies ?? '—'}</p>
              </div>
              <div className="p-3 rounded-xl bg-amber-500/10">
                <Target className="w-6 h-6 text-amber-400" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FlaskConical className="w-5 h-5" />
              Model Evaluation Metrics
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {evalLoading ? (
              <div className="h-64 animate-pulse bg-bg-elevated/50 rounded" />
            ) : evaluation ? (
              <>
                <div className="grid grid-cols-3 gap-4">
                  <MetricCard
                    label="Precision"
                    value={`${(evaluation.evaluation.precision * 100).toFixed(1)}%`}
                    description={`${evaluation.evaluation.anomalies_detected} TP / ${evaluation.evaluation.predicted_anomalies} predicted`}
                    icon={<Target className="w-5 h-5" />}
                    color="blue"
                  />
                  <MetricCard
                    label="Recall"
                    value={`${(evaluation.evaluation.recall * 100).toFixed(1)}%`}
                    description={`${evaluation.evaluation.anomalies_detected} TP / ${evaluation.evaluation.true_anomalies} actual`}
                    icon={<Search className="w-5 h-5" />}
                    color="emerald"
                  />
                  <MetricCard
                    label="F1 Score"
                    value={`${(evaluation.evaluation.f1 * 100).toFixed(1)}%`}
                    description="Harmonic mean of precision & recall"
                    icon={<BarChart2 className="w-5 h-5" />}
                    color="purple"
                  />
                </div>

                <div className="pt-4 border-t border-border">
                  <h4 className="text-sm font-medium text-text-muted mb-3">Confusion Matrix</h4>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-text-muted border-b border-border">
                          <th className="text-left p-2"></th>
                          <th className="text-center p-2">Predicted Normal</th>
                          <th className="text-center p-2">Predicted Anomaly</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr className="border-b border-border">
                          <td className="font-medium p-2">Actual Normal</td>
                          <td className="text-center p-2 font-mono text-text">{evaluation.evaluation.confusion_matrix?.[0]?.[0] ?? '—'}</td>
                          <td className="text-center p-2 font-mono text-red-400">{evaluation.evaluation.confusion_matrix?.[0]?.[1] ?? '—'} FP</td>
                        </tr>
                        <tr>
                          <td className="font-medium p-2">Actual Anomaly</td>
                          <td className="text-center p-2 font-mono text-amber-400">{evaluation.evaluation.confusion_matrix?.[1]?.[0] ?? '—'} FN</td>
                          <td className="text-center p-2 font-mono text-emerald-400">{evaluation.evaluation.confusion_matrix?.[1]?.[1] ?? '—'} TP</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>

                <div className="pt-4 border-t border-border">
                  <h4 className="text-sm font-medium text-text-muted mb-3">Anomaly Score Statistics</h4>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <StatItem label="Min" value={evaluation.evaluation.anomaly_score_stats?.min?.toFixed(4) ?? '—'} />
                    <StatItem label="Max" value={evaluation.evaluation.anomaly_score_stats?.max?.toFixed(4) ?? '—'} />
                    <StatItem label="Mean" value={evaluation.evaluation.anomaly_score_stats?.mean?.toFixed(4) ?? '—'} />
                    <StatItem label="Std Dev" value={evaluation.evaluation.anomaly_score_stats?.std?.toFixed(4) ?? '—'} />
                  </div>
                </div>

                <p className="text-xs text-text-muted text-center pt-4 border-t border-border">{evaluation.note}</p>
              </>
            ) : (
              <div className="text-center py-8 text-text-muted">No evaluation data available</div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="w-5 h-5" />
              Rule vs ML Comparison
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {compLoading ? (
              <div className="h-64 animate-pulse bg-bg-elevated/50 rounded" />
            ) : comparison ? (
              <>
                <div className="grid grid-cols-4 gap-4">
                  <ComparisonCard
                    label="Both Detected"
                    count={comparison.counts.both}
                    color="emerald"
                    icon={<CheckCircle className="w-5 h-5" />}
                  />
                  <ComparisonCard
                    label="Rule Only"
                    count={comparison.counts.rule_only}
                    color="blue"
                    icon={<Shield className="w-5 h-5" />}
                  />
                  <ComparisonCard
                    label="ML Only"
                    count={comparison.counts.ml_only}
                    color="purple"
                    icon={<Brain className="w-5 h-5" />}
                  />
                  <ComparisonCard
                    label="Neither"
                    count={comparison.counts.neither}
                    color="neutral"
                    icon={<XCircle className="w-5 h-5" />}
                  />
                </div>

                <div className="pt-4 border-t border-border">
                  <h4 className="text-sm font-medium text-text-muted mb-3">Detail: Both Detected (Ground Truth)</h4>
                  <Table
                    data={comparison.comparison.both.slice(0, 10)}
                    columns={[
                      { key: 'transaction_id', header: 'TXN ID', render: (row) => `#${row.transaction_id}`, className: 'w-20' },
                      { key: 'amount', header: 'Amount', render: (row) => formatCurrency(row.amount), className: 'w-28' },
                      { key: 'timestamp', header: 'Time', render: (row) => new Date(row.timestamp).toLocaleString(), className: 'w-40' },
                      { key: 'ground_truth', header: 'Ground Truth', render: (row) => (
                        <Badge variant={row.ground_truth ? 'danger' : 'success'}>
                          {row.ground_truth ? 'Anomaly' : 'Normal'}
                        </Badge>
                      ), className: 'w-28' },
                    ]}
                    keyField="transaction_id"
                    emptyMessage="No transactions detected by both"
                  />
                </div>

                <div className="pt-4 border-t border-border">
                  <h4 className="text-sm font-medium text-text-muted mb-3">Detail: ML Only (Potential False Positives / Missed by Rules)</h4>
                  <Table
                    data={comparison.comparison.ml_only.slice(0, 10)}
                    columns={[
                      { key: 'transaction_id', header: 'TXN ID', render: (row) => `#${row.transaction_id}`, className: 'w-20' },
                      { key: 'amount', header: 'Amount', render: (row) => formatCurrency(row.amount), className: 'w-28' },
                      { key: 'timestamp', header: 'Time', render: (row) => new Date(row.timestamp).toLocaleString(), className: 'w-40' },
                      { key: 'ground_truth', header: 'Ground Truth', render: (row) => (
                        <Badge variant={row.ground_truth ? 'danger' : 'warning'}>
                          {row.ground_truth ? 'True Anomaly' : 'False Positive'}
                        </Badge>
                      ), className: 'w-32' },
                    ]}
                    keyField="transaction_id"
                    emptyMessage="No ML-only detections"
                  />
                </div>

                <p className="text-xs text-text-muted text-center pt-4 border-t border-border">
                  Total analyzed: {comparison.total_analyzed} transactions
                </p>
              </>
            ) : (
              <div className="text-center py-8 text-text-muted">No comparison data available</div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Recent Anomaly Details</CardTitle>
          <Badge variant="info">{mlEvents.length} ML anomalies</Badge>
        </CardHeader>
        <CardContent>
          <Table
            data={mlEvents.slice(0, 20)}
            columns={[
              { key: 'time', header: 'Time', render: (row) => new Date(row.timestamp).toLocaleString(), className: 'w-40' },
              { key: 'user', header: 'User', render: (row) => row.user_name, className: 'w-40' },
              { key: 'amount', header: 'Amount', render: (row) => formatCurrency(row.amount), className: 'w-28' },
              { key: 'risk', header: 'ML Risk', render: (row) => (
                <Badge className={getRiskLevelColor(row.ml_result?.risk_level || 'low')}>{getRiskLevelLabel(row.ml_result?.risk_level || 'low')}</Badge>
              ), className: 'w-28' },
              { key: 'score', header: 'Anomaly Score', render: (row) => (
                <span className="font-mono text-sm">{row.ml_result?.anomaly_score?.toFixed(4) ?? '—'}</span>
              ), className: 'w-32' },
              { key: 'ground_truth', header: 'Ground Truth', render: (row) => (
                <Badge variant={row.is_ground_truth_anomaly ? 'danger' : 'success'}>
                  {row.is_ground_truth_anomaly ? 'Confirmed' : 'Normal'}
                </Badge>
              ), className: 'w-28' },
              { key: 'type', header: 'Anomaly Type', render: (row) => row.ground_truth_type ?? '—', className: 'w-32' },
            ]}
            keyField="id"
            emptyMessage="No ML anomalies detected"
          />
        </CardContent>
      </Card>
    </div>
  );
}

function MetricCard({ label, value, description, icon, color }: { label: string; value: string; description: string; icon: React.ReactNode; color: string }) {
  const colors = {
    blue: 'bg-blue-500/10 text-blue-400',
    emerald: 'bg-emerald-500/10 text-emerald-400',
    purple: 'bg-purple-500/10 text-purple-400',
    amber: 'bg-amber-500/10 text-amber-400',
  };
  return (
    <div className="p-4 bg-bg-elevated/50 rounded-lg border border-border/50">
      <div className="flex items-center gap-2 mb-2">
        <span className={cn('p-2 rounded-lg', colors[color as keyof typeof colors] || colors.blue)}>
          {icon}
        </span>
      </div>
      <p className="text-2xl font-bold text-text">{value}</p>
      <p className="text-xs text-text-muted">{label}</p>
      <p className="text-[10px] text-text-subtle mt-1">{description}</p>
    </div>
  );
}

function ComparisonCard({ label, count, color, icon }: { label: string; count: number; color: string; icon: React.ReactNode }) {
  const colors = {
    emerald: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    blue: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
    purple: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
    neutral: 'bg-bg-elevated text-text-muted border-border',
  };
  return (
    <div className={cn('p-4 rounded-lg border text-center', colors[color as keyof typeof colors] || colors.neutral)}>
      <div className="flex items-center justify-center gap-2 mb-2">
        {icon}
      </div>
      <p className="text-3xl font-bold text-text">{count}</p>
      <p className="text-xs text-text-muted">{label}</p>
    </div>
  );
}

function StatItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="p-3 bg-bg-elevated/50 rounded-lg border border-border/50 text-center">
      <p className="text-lg font-bold text-text font-mono">{value}</p>
      <p className="text-xs text-text-muted">{label}</p>
    </div>
  );
}