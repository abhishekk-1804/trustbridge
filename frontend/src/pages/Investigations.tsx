import * as React from 'react';
import { useParams, Link } from 'react-router-dom';
import { useRiskEvent, useExplainRisk } from '@/api';
import { formatCurrency, formatRelativeTime, formatDate, getRiskLevelColor, getRiskLevelLabel, getStatusColor } from '@/utils';
import { cn } from '@/utils';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Table, Column } from '@/components/ui/Table';
import { ArrowLeft, AlertTriangle, Search, User, DollarSign, CreditCard, Shield, Clock, MapPin, Tag, Info, CheckCircle } from 'lucide-react';

export function Investigations() {
  const { eventId } = useParams<{ eventId: string }>();
  const id = Number(eventId);
  const { data: event, isLoading, error } = useRiskEvent(id);
  const { data: explanation, isLoading: explainLoading } = useExplainRisk(id);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Link to="/risk" className="p-2 text-text-muted hover:text-text transition-colors rounded-lg hover:bg-bg-elevated">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-semibold text-text">Loading investigation...</h1>
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

  if (error || !event) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Link to="/risk" className="p-2 text-text-muted hover:text-text transition-colors rounded-lg hover:bg-bg-elevated">
            <ArrowLeft className="w-5 h-5" />
          </Link>
        </div>
        <Card>
          <CardContent className="py-12 text-center">
            <AlertTriangle className="w-12 h-12 text-text-muted mx-auto mb-4" />
            <h2 className="text-lg font-medium text-text">Investigation Not Found</h2>
            <p className="text-text-muted mt-2">The requested risk event could not be found.</p>
            <Link to="/risk" className="mt-4 inline-flex items-center gap-2 text-primary hover:underline">
              <ArrowLeft className="w-4 h-4" />
              Back to Risk Intelligence
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  const isPayment = event.type === 'payment';
  const riskLevel = event.risk_level || event.ml_result?.risk_level || 'unknown';

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-4">
          <Link to="/risk" className="p-2 text-text-muted hover:text-text transition-colors rounded-lg hover:bg-bg-elevated">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-semibold text-text">Investigation #{event.id}</h1>
            <p className="text-text-muted">Risk event analysis and evidence</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Badge className={cn('gap-1', getRiskLevelColor(riskLevel))}>
            <AlertTriangle className="w-4 h-4" />
            {getRiskLevelLabel(riskLevel)}
          </Badge>
          <Badge variant={event.final_decision === 'rejected' ? 'danger' : event.final_decision === 'flagged' ? 'warning' : 'success'}>
            {event.final_decision?.toUpperCase() ?? 'UNKNOWN'}
          </Badge>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Event Summary</CardTitle>
              <CardDescription>Key details about this risk event</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="p-4 bg-bg-elevated/50 rounded-lg border border-border/50">
                  <p className="text-xs text-text-muted uppercase tracking-wide">Event ID</p>
                  <p className="font-mono text-text mt-1">#{event.id}</p>
                </div>
                <div className="p-4 bg-bg-elevated/50 rounded-lg border border-border/50">
                  <p className="text-xs text-text-muted uppercase tracking-wide">Timestamp</p>
                  <p className="font-medium text-text mt-1">{formatDate(event.timestamp)}</p>
                </div>
                <div className="p-4 bg-bg-elevated/50 rounded-lg border border-border/50">
                  <p className="text-xs text-text-muted uppercase tracking-wide">Amount</p>
                  <p className="font-mono text-text mt-1">{formatCurrency(event.amount)}</p>
                </div>
                <div className="p-4 bg-bg-elevated/50 rounded-lg border border-border/50">
                  <p className="text-xs text-text-muted uppercase tracking-wide">Type</p>
                  <p className="font-medium text-text mt-1 capitalize">{event.transaction_type}</p>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-border">
                <span className="text-sm text-text-muted">Reason:</span>
                <p className="text-sm text-text">{event.reason}</p>
              </div>

              {event.ground_truth_type && (
                <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-border">
                  <span className="text-sm text-text-muted">Ground Truth:</span>
                  <Badge variant={event.is_ground_truth_anomaly ? 'danger' : 'success'}>
                    {event.is_ground_truth_anomaly ? 'Confirmed Anomaly' : 'Normal Transaction'}
                    {event.ground_truth_type && ` (${event.ground_truth_type})`}
                  </Badge>
                </div>
              )}
            </CardContent>
          </Card>

          {event.fraud_rule && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Shield className="w-5 h-5 text-blue-400" />
                  Rule-Based Detection
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <p className="text-xs text-text-muted">Flagged</p>
                    <p className="font-medium text-text">{event.fraud_rule.flagged ? 'Yes' : 'No'}</p>
                  </div>
                  <div>
                    <p className="text-xs text-text-muted">Risk Level</p>
                    <Badge className={getRiskLevelColor(event.fraud_rule.risk_level)}>{getRiskLevelLabel(event.fraud_rule.risk_level)}</Badge>
                  </div>
                  <div>
                    <p className="text-xs text-text-muted">Amount</p>
                    <p className="font-mono text-text">{formatCurrency(event.fraud_rule.transaction_amount ?? 0)}</p>
                  </div>
                  <div>
                    <p className="text-xs text-text-muted">Reference Avg</p>
                    <p className="font-mono text-text">{event.fraud_rule.reference_average ? formatCurrency(event.fraud_rule.reference_average) : '—'}</p>
                  </div>
                </div>
                <div className="pt-2 border-t border-border">
                  <p className="text-xs text-text-muted">Reason: {event.fraud_rule.reason}</p>
                </div>
                {event.fraud_rule.ratio && (
                  <div className="pt-2 border-t border-border">
                    <p className="text-xs text-text-muted">Ratio: {event.fraud_rule.ratio.toFixed(2)}x (multiplier: {event.fraud_rule.multiplier_used?.toFixed(1)}x)</p>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {event.ml_result && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Search className="w-5 h-5 text-purple-400" />
                  ML Anomaly Detection
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <p className="text-xs text-text-muted">Anomaly Detected</p>
                    <p className="font-medium text-text">{event.ml_result.is_anomaly ? 'Yes' : 'No'}</p>
                  </div>
                  <div>
                    <p className="text-xs text-text-muted">Risk Level</p>
                    <Badge className={getRiskLevelColor(event.ml_result.risk_level)}>{getRiskLevelLabel(event.ml_result.risk_level)}</Badge>
                  </div>
                  <div>
                    <p className="text-xs text-text-muted">Anomaly Score</p>
                    <p className="font-mono text-text">{event.ml_result.anomaly_score.toFixed(4)}</p>
                  </div>
                  <div>
                    <p className="text-xs text-text-muted">Threshold</p>
                    <p className="font-mono text-text">~0.5 (Isolation Forest)</p>
                  </div>
                </div>
                <div className="pt-2 border-t border-border">
                  <p className="text-xs text-text-muted">
                    <span className="font-medium">Note:</span> Isolation Forest scores closer to 1 indicate higher anomaly likelihood.
                    Contributing features are not directly attributable due to ensemble nature.
                  </p>
                </div>
              </CardContent>
            </Card>
          )}

          {explanation && !explainLoading && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Info className="w-5 h-5 text-primary" />
                  Explainability Indicators
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {explanation.contributing_indicators && explanation.contributing_indicators.length > 0 ? (
                  <ul className="space-y-2">
                    {explanation.contributing_indicators.map((indicator: string, idx: number) => (
                      <li key={idx} className="flex items-start gap-2 p-3 bg-bg-elevated/50 rounded-lg border border-border/50">
                        <Info className="w-4 h-4 text-primary mt-0.5 flex-shrink-0" />
                        <span className="text-sm text-text">{indicator}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-text-muted text-sm">No specific contributing indicators identified.</p>
                )}
                {explanation.note && (
                  <p className="text-xs text-text-muted pt-2 border-t border-border">{explanation.note}</p>
                )}
              </CardContent>
            </Card>
          )}
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <User className="w-5 h-5" />
                User Profile
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <Link to={`/trust/${event.user_id}`} className="flex items-center gap-3 p-3 bg-bg-elevated/50 rounded-lg border border-border/50 hover:border-primary/50 transition-colors">
                <div className="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center">
                  <User className="w-5 h-5 text-primary" />
                </div>
                <div>
                  <p className="font-medium text-text">{event.user_name}</p>
                  <p className="text-xs text-text-muted">User ID: {event.user_id}</p>
                </div>
              </Link>
              <div className="grid grid-cols-2 gap-3 pt-2 border-t border-border">
                <div>
                  <p className="text-xs text-text-muted">Event ID</p>
                  <p className="font-mono text-sm text-text">#{event.id}</p>
                </div>
                <div>
                  <p className="text-xs text-text-muted">Source</p>
                  <p className="text-sm text-text capitalize">{event.rule_result && event.ml_result ? 'Both' : event.rule_result ? 'Rule' : 'ML'}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <DollarSign className="w-5 h-5" />
                Transaction Details
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {isPayment ? (
                <>
                  <div className="p-3 bg-bg-elevated/50 rounded-lg border border-border/50">
                    <p className="text-xs text-text-muted">Reference ID</p>
                    <p className="font-mono text-sm text-text break-all">{event.reference_id}</p>
                  </div>
                  <div className="p-3 bg-bg-elevated/50 rounded-lg border border-border/50">
                    <p className="text-xs text-text-muted">Payment Method</p>
                    <p className="text-sm text-text capitalize">{event.payment_method?.replace('_', ' ') ?? '—'}</p>
                  </div>
                  <div className="p-3 bg-bg-elevated/50 rounded-lg border border-border/50">
                    <p className="text-xs text-text-muted">Status</p>
                    <Badge className={getStatusColor(event.status)}>{event.status}</Badge>
                  </div>
                  {event.risk_policy_decision && (
                    <div className="p-3 bg-bg-elevated/50 rounded-lg border border-border/50">
                      <p className="text-xs text-text-muted">Risk Decision</p>
                      <Badge variant={
                        event.risk_policy_decision === 'reject' ? 'danger' :
                        event.risk_policy_decision === 'flag' ? 'warning' : 'success'
                      }>{event.risk_policy_decision.toUpperCase()}</Badge>
                    </div>
                  )}
                  {event.trust_score !== null && event.trust_score !== undefined && (
                    <div className="p-3 bg-bg-elevated/50 rounded-lg border border-border/50">
                      <p className="text-xs text-text-muted">Trust Score at Payment</p>
                      <p className="text-2xl font-bold text-text">{event.trust_score.toFixed(1)}</p>
                    </div>
                  )}
                </>
              ) : (
                <>
                  <div className="p-3 bg-bg-elevated/50 rounded-lg border border-border/50">
                    <p className="text-xs text-text-muted">Merchant</p>
                    <p className="text-sm text-text">{event.merchant ?? '—'}</p>
                  </div>
                  <div className="p-3 bg-bg-elevated/50 rounded-lg border border-border/50">
                    <p className="text-xs text-text-muted">Category</p>
                    <p className="text-sm text-text">{event.category ?? '—'}</p>
                  </div>
                  <div className="p-3 bg-bg-elevated/50 rounded-lg border border-border/50">
                    <p className="text-xs text-text-muted">Location</p>
                    <p className="text-sm text-text">{event.city ?? '—'}</p>
                  </div>
                  <div className="p-3 bg-bg-elevated/50 rounded-lg border border-border/50">
                    <p className="text-xs text-text-muted">Anomaly Flag</p>
                    <Badge variant={event.is_anomaly ? 'danger' : 'success'}>
                      {event.is_anomaly ? 'Anomaly' : 'Normal'}
                    </Badge>
                  </div>
                  {event.anomaly_type && (
                    <div className="p-3 bg-bg-elevated/50 rounded-lg border border-border/50">
                      <p className="text-xs text-text-muted">Anomaly Type</p>
                      <p className="text-sm text-text">{event.anomaly_type}</p>
                    </div>
                  )}
                </>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Clock className="w-5 h-5" />
                Timeline
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-start gap-3 p-3 bg-bg-elevated/50 rounded-lg border border-border/50">
                <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center flex-shrink-0">
                  <AlertTriangle className="w-4 h-4 text-primary" />
                </div>
                <div>
                  <p className="font-medium text-text">Risk Event Created</p>
                  <p className="text-xs text-text-muted">{formatDate(event.timestamp)}</p>
                </div>
              </div>
              {isPayment && event.completed_at && (
                <div className="flex items-start gap-3 p-3 bg-bg-elevated/50 rounded-lg border border-border/50">
                  <div className="w-8 h-8 rounded-full bg-emerald/20 flex items-center justify-center flex-shrink-0">
                    <CheckCircle className="w-4 h-4 text-emerald-400" />
                  </div>
                  <div>
                    <p className="font-medium text-text">Payment {event.status === 'completed' ? 'Completed' : 'Processed'}</p>
                    <p className="text-xs text-text-muted">{formatDate(event.completed_at)}</p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}