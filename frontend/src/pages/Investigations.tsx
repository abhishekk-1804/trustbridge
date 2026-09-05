import * as React from 'react';
import { useParams, Link } from 'react-router-dom';
import { useRiskEvent, useExplainRisk } from '@/api';
import { useInvestigationCase, useCreateInvestigationCase, useUpdateInvestigationCase, useInvestigationAuditLog } from '@/api';
import { formatCurrency, formatRelativeTime, formatDate, getRiskLevelColor, getRiskLevelLabel, getStatusColor } from '@/utils';
import { cn } from '@/utils';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Table, Column } from '@/components/ui/Table';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { Textarea } from '@/components/ui/Textarea';
import { ArrowLeft, AlertTriangle, Search, User, DollarSign, CreditCard, Shield, Clock, MapPin, Tag, Info, CheckCircle, ChevronRight, ChevronLeft, FileText, Pencil, Save, X, Loader2, ArrowRight, Plus } from 'lucide-react';
import type { CaseStatus, CaseDecision, InvestigationCase } from '@/types';

const CASE_STATUS_LABELS: Record<CaseStatus, string> = {
  pending: 'Pending',
  under_review: 'Under Review',
  resolved: 'Resolved',
  escalated: 'Escalated',
  dismissed: 'Dismissed',
};

const CASE_DECISION_LABELS: Record<CaseDecision, string> = {
  true_positive: 'True Positive',
  false_positive: 'False Positive',
  inconclusive: 'Inconclusive',
  escalated: 'Escalated',
};

const STATUS_TRANSITIONS: Record<CaseStatus, CaseStatus[]> = {
  pending: ['under_review', 'escalated', 'dismissed'],
  under_review: ['pending', 'resolved', 'escalated', 'dismissed'],
  resolved: [],
  escalated: ['resolved', 'dismissed'],
  dismissed: [],
};

const DECISION_OPTIONS_BY_STATUS: Record<CaseStatus, (CaseDecision | null)[]> = {
  pending: [null],
  under_review: [null],
  resolved: ['true_positive', 'false_positive', 'inconclusive'],
  escalated: ['escalated', null],
  dismissed: ['false_positive', null],
};

export function Investigations() {
  const { eventId } = useParams<{ eventId: string }>();
  const riskEventId = Number(eventId);

  // Risk event evidence (read-only)
  const { data: event, isLoading: eventLoading, error: eventError } = useRiskEvent(riskEventId);
  const { data: explanation, isLoading: explainLoading } = useExplainRisk(riskEventId);

  // Investigation case state
  const [caseId, setCaseId] = React.useState<number | null>(null);
  const [showCreateCase, setShowCreateCase] = React.useState(false);
  const [isCreatingCase, setIsCreatingCase] = React.useState(false);

  // Determine risk event type and ID for case creation
  const riskEventType = event?.type === 'payment' ? 'payment' : 'transaction';

  // Case data and mutations
  const { data: investigationCase, isLoading: caseLoading, error: caseError, refetch: refetchCase } =
    useInvestigationCase(caseId ?? 0);

  const createCaseMutation = useCreateInvestigationCase();
  const updateCaseMutation = useUpdateInvestigationCase();
  const { data: auditLogs, isLoading: auditLoading } = useInvestigationAuditLog(caseId ?? 0);

  // Local state for form
  const [status, setStatus] = React.useState<InvestigationCase['status']>('pending');
  const [decision, setDecision] = React.useState<InvestigationCase['decision']>(null);
  const [notes, setNotes] = React.useState('');
  const [isSaving, setIsSaving] = React.useState(false);
  const [saveError, setSaveError] = React.useState<string | null>(null);

  // Sync local state with investigation case when it loads
  React.useEffect(() => {
    if (investigationCase) {
      setStatus(investigationCase.status);
      setDecision(investigationCase.decision);
      setNotes(investigationCase.notes ?? '');
    }
  }, [investigationCase]);

  const handleCreateCase = async () => {
    if (!riskEventId) return;
    setIsCreatingCase(true);
    setSaveError(null);
    try {
      const newCase = await createCaseMutation.mutateAsync({
        risk_event_id: riskEventId,
        risk_event_type: riskEventType,
      });
      setCaseId(newCase.id);
      setShowCreateCase(false);
    } catch (err: any) {
      setSaveError(err.message || 'Failed to create investigation case');
    } finally {
      setIsCreatingCase(false);
    }
  };

  const handleSave = async () => {
    if (!caseId) return;
    setIsSaving(true);
    setSaveError(null);
    try {
      await updateCaseMutation.mutateAsync({
        caseId,
        update: { status, decision: decision ?? undefined, notes },
      });
      await refetchCase();
    } catch (err: any) {
      setSaveError(err.message || 'Failed to save investigation case');
    } finally {
      setIsSaving(false);
    }
  };

  const handleStatusChange = (newStatus: CaseStatus) => {
    setStatus(newStatus);
    // Auto-set decision based on status rules
    if (newStatus === 'resolved' && !['true_positive', 'false_positive', 'inconclusive'].includes(decision ?? '')) {
      setDecision('true_positive');
    } else if (newStatus === 'escalated' && decision !== 'escalated') {
      setDecision('escalated');
    } else if (newStatus === 'dismissed' && decision !== 'false_positive') {
      setDecision('false_positive');
    } else if (newStatus === 'pending' || newStatus === 'under_review') {
      setDecision(null);
    }
  };

  const handleDecisionChange = (newDecision: CaseDecision | null) => {
    setDecision(newDecision);
  };

  const handleNotesChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setNotes(e.target.value);
  };

  const getDecisionLabel = (d: CaseDecision | null) => {
    if (!d) return '—';
    return CASE_DECISION_LABELS[d];
  };

  const getStatusLabel = (s: CaseStatus) => {
    return CASE_STATUS_LABELS[s];
  };

  if (eventLoading) {
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

  if (eventError || !event) {
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

  // Determine if we should show case creation prompt
  const hasCase = !!caseId;
  const caseExistsForEvent = caseId && investigationCase?.risk_event_id === riskEventId;

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

      {/* Case Management Section */}
      <Card className="border-primary/30 bg-primary-bg/30">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <FileText className="w-5 h-5" />
            Investigation Case
          </CardTitle>
          <div className="flex items-center gap-2">
            {caseLoading && <Loader2 className="w-4 h-4 animate-spin" />}
            {hasCase && investigationCase && (
              <Badge variant={
                investigationCase.status === 'resolved' ? 'success' :
                investigationCase.status === 'dismissed' ? 'danger' :
                investigationCase.status === 'escalated' ? 'warning' :
                investigationCase.status === 'under_review' ? 'info' : 'neutral'
              } className="gap-1">
                {CASE_STATUS_LABELS[investigationCase.status]}
              </Badge>
            )}
            {hasCase ? (
              <>
                {investigationCase?.decision && (
                  <Badge variant="neutral" className="gap-1">
                    {CASE_DECISION_LABELS[investigationCase.decision!]}
                  </Badge>
                )}
              </>
            ) : (
              <Button
                variant="primary"
                onClick={() => setShowCreateCase(true)}
                disabled={isCreatingCase}
              >
                <Plus className="w-4 h-4" />
                Create Investigation Case
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {saveError && (
            <div className="p-4 bg-danger-bg border border-danger-border rounded-lg text-sm text-danger flex items-center gap-2">
              <AlertTriangle className="w-4 h-4" />
              {saveError}
            </div>
          )}

          {!hasCase && !showCreateCase && (
            <div className="p-6 bg-bg-elevated/50 border border-border/50 rounded-lg text-center">
              <FileText className="w-12 h-12 text-text-muted mx-auto mb-4" />
              <h3 className="text-lg font-medium text-text mb-2">No Investigation Case Yet</h3>
              <p className="text-text-muted mb-4">
                Create an investigation case to track the analyst workflow for this risk event.
              </p>
              <Button
                variant="primary"
                onClick={() => setShowCreateCase(true)}
                disabled={isCreatingCase}
              >
                <Plus className="w-4 h-4 mr-2" />
                Create Investigation Case
              </Button>
            </div>
          )}

          {showCreateCase && !hasCase && (
            <div className="p-4 bg-primary-bg border border-primary-border rounded-lg space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="font-medium text-text">Create Investigation Case</h3>
                <Button variant="ghost" size="sm" onClick={() => setShowCreateCase(false)}>
                  <X className="w-4 h-4" />
                </Button>
              </div>
              <p className="text-sm text-text-muted">
                This will create an investigation case for risk event <strong>#{riskEventId}</strong> ({riskEventType}).
              </p>
              <div className="flex gap-3">
                <Button
                  variant="primary"
                  onClick={handleCreateCase}
                  disabled={isCreatingCase}
                >
                  {isCreatingCase ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin mr-2" />
                      Creating...
                    </>
                  ) : (
                    <>
                      <Plus className="w-4 h-4 mr-2" />
                      Create Investigation Case
                    </>
                  )}
                </Button>
                <Button variant="secondary" onClick={() => setShowCreateCase(false)}>
                  Cancel
                </Button>
              </div>
              {isCreatingCase && <div className="h-2 bg-primary/20 animate-pulse rounded" />}
            </div>
          )}

          {hasCase && investigationCase && (
            <div className="space-y-6">
              {/* Case Status & Controls */}
              <div className="p-4 bg-bg-elevated/50 border border-border/50 rounded-lg space-y-4">
                <div className="flex flex-wrap items-center gap-4">
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-medium text-text-muted">Status:</span>
                    <Badge variant={
                      investigationCase.status === 'resolved' ? 'success' :
                      investigationCase.status === 'dismissed' ? 'danger' :
                      investigationCase.status === 'escalated' ? 'warning' :
                      investigationCase.status === 'under_review' ? 'info' : 'neutral'
                    } className="gap-1 text-sm">
                      {CASE_STATUS_LABELS[investigationCase.status]}
                    </Badge>
                  </div>
                  {investigationCase.decision && (
                    <Badge variant="neutral" className="gap-1 text-sm">
                      {CASE_DECISION_LABELS[investigationCase.decision]}
                    </Badge>
                  )}
                  <span className="text-xs text-text-muted">
                    Updated: {formatRelativeTime(investigationCase.updated_at)}
                    {investigationCase.resolved_at && ` • Resolved: ${formatRelativeTime(investigationCase.resolved_at)}`}
                  </span>
                </div>

                {/* Status Transition Controls */}
                <div className="flex flex-wrap items-center gap-3">
                  <span className="text-sm font-medium text-text-muted">Change Status:</span>
                  {STATUS_TRANSITIONS[investigationCase.status]?.map((nextStatus) => (
                    <Button
                      key={nextStatus}
                      variant={investigationCase.status === nextStatus ? 'primary' : 'secondary'}
                      size="sm"
                      onClick={() => handleStatusChange(nextStatus)}
                      disabled={updateCaseMutation.isPending}
                    >
                      {CASE_STATUS_LABELS[nextStatus]}
                    </Button>
                  ))}
                </div>

                {/* Decision Selector (shown when relevant) */}
                {['resolved', 'escalated', 'dismissed'].includes(investigationCase.status) && (
                  <div className="flex flex-wrap items-center gap-3">
                    <label className="text-sm font-medium text-text-muted">Decision:</label>
                    <Select
                      value={investigationCase.decision ?? ''}
                      onChange={(e) => handleDecisionChange(e.target.value as CaseDecision | null)}
                      options={DECISION_OPTIONS_BY_STATUS[investigationCase.status].map(d => ({
                        value: d ?? '',
                        label: d ? CASE_DECISION_LABELS[d] : '— (unset)',
                      }))}
                      disabled={updateCaseMutation.isPending}
                    />
                  </div>
                )}
              </div>

              {/* Notes Section */}
              <div className="p-4 bg-bg-elevated/50 border border-border/50 rounded-lg space-y-3">
                <label className="block text-sm font-medium text-text-muted">Analyst Notes</label>
                <Textarea
                  value={notes}
                  onChange={handleNotesChange}
                  placeholder="Add investigation notes, findings, or rationale..."
                  rows={4}
                  disabled={updateCaseMutation.isPending}
                />
                <div className="flex items-center gap-3">
                  <Button
                    variant="primary"
                    onClick={handleSave}
                    disabled={updateCaseMutation.isPending || isSaving}
                  >
                    {updateCaseMutation.isPending || isSaving ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin mr-2" />
                        Saving...
                      </>
                    ) : (
                      <>
                        <Save className="w-4 h-4 mr-2" />
                        Save Changes
                      </>
                    )}
                  </Button>
                  {saveError && (
                    <span className="text-sm text-danger flex items-center gap-1">
                      <AlertTriangle className="w-4 h-4" />
                      {saveError}
                    </span>
                  )}
                </div>
              </div>

              {/* Audit Timeline */}
              <div className="space-y-3">
                <h4 className="text-sm font-medium text-text-muted mb-3">Audit Timeline</h4>
                {auditLoading ? (
                  <div className="h-32 animate-pulse bg-bg-elevated/50 rounded" />
                ) : auditLogs && auditLogs.length > 0 ? (
                  <div className="space-y-2">
                    {auditLogs.map((log) => (
                      <AuditLogEntry key={log.id} log={log} />
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-text-muted text-center py-4">No audit entries yet</p>
                )}
              </div>
            </div>
          )}

          {caseError && hasCase && (
            <div className="p-4 bg-danger-bg border border-danger-border rounded-lg text-sm text-danger flex items-center gap-2">
              <AlertTriangle className="w-4 h-4" />
              Failed to load investigation case: {caseError.message}
            </div>
          )}

          {createCaseMutation.isError && showCreateCase && (
            <div className="p-4 bg-danger-bg border border-danger-border rounded-lg text-sm text-danger flex items-center gap-2">
              <AlertTriangle className="w-4 h-4" />
              {createCaseMutation.error?.message || 'Failed to create investigation case'}
            </div>
          )}
        </CardContent>
      </Card>

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
                  {event.payment_id && (
                    <Link to={`/ledger/${event.payment_id}`} className="inline-flex items-center gap-2 text-primary hover:underline text-sm mt-2">
                      <ChevronRight className="w-4 h-4" />
                      View Ledger
                    </Link>
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

function AuditLogEntry({ log }: { log: { id: number; action: string; old_state: string | null; new_state: string | null; timestamp: string } }) {
  const parseState = (state: string | null) => {
    if (!state) return null;
    try {
      return JSON.parse(state);
    } catch {
      return { raw: state };
    }
  };

  const oldState = parseState(log.old_state);
  const newState = parseState(log.new_state);

  const getActionLabel = (action: string) => {
    switch (action) {
      case 'case_created': return 'Case Created';
      case 'case_updated': return 'Case Updated';
      default: return action;
    }
  };

  const renderState = (state: any, label: string) => {
    if (!state) return <span className="text-text-muted">—</span>;
    if (state.raw) return <span className="text-text-muted text-xs">{state.raw}</span>;
    if (typeof state === 'object' && Object.keys(state).length === 0) return <span className="text-text-muted">—</span>;
    const entries = Object.entries(state) as [string, unknown][];
    return (
      <div className="flex flex-wrap gap-2 text-xs">
        {entries.map(([key, value]) => (
          <span key={key} className="bg-bg-elevated/50 px-2 py-1 rounded text-text">
            {key}: <span className="font-mono">{String(typeof value === 'object' && value !== null ? JSON.stringify(value) : (value ?? '—'))}</span>
          </span>
        ))}
      </div>
    );
  };

  return (
    <div className="p-3 bg-bg-elevated/50 border border-border/50 rounded-lg">
      <div className="flex flex-wrap items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-2">
          <Badge variant="neutral" className="text-xs">
            {log.action === 'case_created' ? (
              <>
                <CheckCircle className="w-3 h-3 mr-1 text-emerald-400" />
              </>
            ) : (
              <>
                <Pencil className="w-3 h-3 mr-1 text-primary" />
              </>
            )}
            {getActionLabel(log.action)}
          </Badge>
        </div>
        <span className="text-[10px] text-text-muted">
          {formatRelativeTime(log.timestamp)}
        </span>
      </div>
      <div className="grid grid-cols-2 gap-4 text-xs">
        <div>
          <p className="text-text-muted mb-1">Before</p>
          {renderState(oldState, 'Before')}
        </div>
        <div>
          <p className="text-text-muted mb-1">After</p>
          {renderState(newState, 'After')}
        </div>
      </div>
    </div>
  );
}