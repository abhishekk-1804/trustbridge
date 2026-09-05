export interface User {
  id: number;
  name: string;
  email: string;
  role: 'delivery_partner' | 'freelancer' | 'student';
  account_created_at: string;
  is_verified: boolean;
  accounts?: Account[];
}

export interface Account {
  id: number;
  user_id: number;
  account_type: string;
  balance: number;
  currency: string;
  status: 'active' | 'frozen' | 'closed';
  created_at: string;
}

export interface Transaction {
  id: number;
  user_id: number;
  account_id: number;
  amount: number;
  transaction_type: 'debit' | 'credit';
  status: 'success' | 'failed';
  payment_method: string;
  merchant_category: string | null;
  merchant_name: string | null;
  location_city: string | null;
  description: string | null;
  timestamp: string;
  is_anomaly: boolean;
  anomaly_type: string | null;
}

export interface PaymentTransaction {
  id: number;
  reference_id: string;
  idempotency_key: string;
  sender_account_id: number;
  receiver_account_id: number;
  amount: number;
  currency: string;
  payment_method: 'upi_simulated' | 'bank_transfer_simulated' | 'wallet_simulated';
  status: 'pending' | 'completed' | 'failed' | 'rejected' | 'reversed';
  trust_score: number | null;
  fraud_rule_flagged: boolean;
  fraud_rule_reason: string | null;
  ml_anomaly_score: number | null;
  ml_is_anomaly: boolean;
  risk_policy_decision: string | null;
  failure_reason: string | null;
  created_at: string;
  completed_at: string | null;
  ledger_entries: LedgerEntry[];
}

export interface LedgerEntry {
  id: number;
  payment_transaction_id: number;
  account_id: number;
  entry_type: 'debit' | 'credit';
  amount: number;
  balance_after: number;
  description: string | null;
  created_at: string;
}

export interface TrustScoreResponse {
  user_id: number;
  user_name: string;
  trust_score: number;
  verdict: string;
  components: Record<string, {
    score: number;
    weight: number;
    contribution: number;
  }>;
}

export interface TrustComponents {
  payment_reliability: {
    score: number;
    weight: number;
    contribution: number;
  };
  transaction_consistency: {
    score: number;
    weight: number;
    contribution: number;
  };
  account_behaviour: {
    score: number;
    weight: number;
    contribution: number;
  };
}

export interface FraudRuleResult {
  flagged: boolean;
  risk_level: string;
  reason: string;
  transaction_id?: number;
  transaction_amount?: number;
  reference_average?: number;
  ratio?: number;
  multiplier_used?: number;
}

export interface MLAnomalyResult {
  anomaly_score: number;
  is_anomaly: boolean;
  risk_level: string;
}

export interface RiskAssessment {
  trust_score: number;
  trust_components: Record<string, any>;
  fraud_rule: FraudRuleResult | null;
  ml_anomaly: MLAnomalyResult | null;
  risk_level: 'low' | 'moderate' | 'high';
  risk_drivers: string[];
  risk_decision: 'proceed' | 'flag' | 'reject';
}

export interface RiskEvent {
  id: number;
  user_id: number;
  user_name: string;
  amount: number;
  transaction_type: 'debit' | 'credit';
  risk_level: 'low' | 'moderate' | 'high';
  rule_result: FraudRuleResult | null;
  ml_result: MLAnomalyResult | null;
  final_decision: string;
  reason: string;
  timestamp: string;
  is_ground_truth_anomaly: boolean;
  ground_truth_type: string | null;
}

export interface ModelEvaluation {
  model: string;
  version: string;
  evaluation: {
    precision: number;
    recall: number;
    f1: number;
    confusion_matrix: number[][];
    total_transactions: number;
    true_anomalies: number;
    predicted_anomalies: number;
    anomalies_detected: number;
    false_positives: number;
    false_negatives: number;
    anomaly_score_stats: {
      min: number;
      max: number;
      mean: number;
      std: number;
    };
    detected_details: Array<{ transaction_id: number; anomaly_score: number }>;
    false_positive_details: Array<{ transaction_id: number; anomaly_score: number }>;
    false_negative_details: Array<{ transaction_id: number; anomaly_score: number }>;
  };
  note: string;
}

export interface RuleVsMLComparison {
  comparison: {
    comparison: {
      both: Array<{ transaction_id: number; amount: number; timestamp: string; ground_truth: boolean }>;
      rule_only: Array<{ transaction_id: number; amount: number; timestamp: string; ground_truth: boolean }>;
      ml_only: Array<{ transaction_id: number; amount: number; timestamp: string; ground_truth: boolean }>;
      neither: Array<{ transaction_id: number; amount: number; timestamp: string; ground_truth: boolean }>;
    };
    counts: {
      both: number;
      rule_only: number;
      ml_only: number;
      neither: number;
    };
    total_analyzed: number;
  };
  description: string;
}

export interface DashboardSummary {
  total_users: number;
  total_transactions: number;
  active_risk_events: number;
  system_health: string;
  trust_distribution: Record<string, number>;
  recent_transactions_count: number;
}

export interface LiveRiskEvent {
  id: number;
  user_id: number;
  user_name: string;
  amount: number;
  risk_level: string;
  source: string;
  timestamp: string;
  reason: string;
}

export interface RecentTransaction {
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

export interface SimulatePaymentRequest {
  sender_account_id: number;
  receiver_account_id: number;
  amount: number;
  payment_method: 'upi_simulated' | 'bank_transfer_simulated' | 'wallet_simulated';
  idempotency_key: string;
}

export interface SimulatePaymentResponse {
  payment_id: number;
  reference_id: string;
  status: string;
  amount: number;
  sender_account_id: number;
  receiver_account_id: number;
  payment_method: string;
  trust_score: number | null;
  fraud_rule_flagged: boolean;
  fraud_rule_reason: string | null;
  ml_anomaly_score: number | null;
  ml_is_anomaly: boolean;
  risk_policy_decision: string | null;
  failure_reason: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface ApiError {
  error: string;
  code: string;
  [key: string]: any;
}

export interface CopilotRequest {
  query: string;
  user_id?: number;
  transaction_id?: number;
  payment_id?: number;
  conversation_history?: Array<{ user?: string; assistant?: string }>;
}

export interface CopilotResponse {
  response: string;
  intent: string;
  context_used: Record<string, any>;
  ai_available: boolean;
}

export type CaseStatus = 'pending' | 'under_review' | 'resolved' | 'escalated' | 'dismissed';

export type CaseDecision = 'true_positive' | 'false_positive' | 'inconclusive' | 'escalated';

export type RiskEventType = 'transaction' | 'payment';

export interface InvestigationCase {
  id: number;
  risk_event_id: number;
  risk_event_type: RiskEventType;
  status: CaseStatus;
  analyst_id: number | null;
  notes: string | null;
  decision: CaseDecision | null;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
}

export interface InvestigationCaseCreate {
  risk_event_id: number;
  risk_event_type: RiskEventType;
}

export interface InvestigationCaseUpdate {
  status?: CaseStatus;
  notes?: string;
  decision?: CaseDecision;
}

export interface AuditLogEntry {
  id: number;
  case_id: number;
  user_id: number | null;
  action: string;
  old_state: string | null;
  new_state: string | null;
  timestamp: string;
}