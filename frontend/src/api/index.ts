import axios, { type AxiosInstance, type AxiosError, type InternalAxiosRequestConfig } from 'axios';
import type {
  User,
  Account,
  Transaction,
  PaymentTransaction,
  LedgerEntry,
  TrustScoreResponse,
  RiskAssessment,
  RiskEvent,
  ModelEvaluation,
  RuleVsMLComparison,
  DashboardSummary,
  LiveRiskEvent,
  RecentTransaction,
  SimulatePaymentRequest,
  SimulatePaymentResponse,
  ApiError,
  CopilotRequest,
  CopilotResponse,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 30000,
    });

    this.client.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        return config;
      },
      (error) => Promise.reject(error)
    );

    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError<ApiError>) => {
        if (error.response) {
          const message = error.response.data?.error || error.message;
          return Promise.reject(new Error(`${error.response.status}: ${message}`));
        }
        return Promise.reject(error);
      }
    );
  }

  // Dashboard
  async getDashboardSummary(): Promise<DashboardSummary> {
    const { data } = await this.client.get('/dashboard/summary');
    return data;
  }

  async getRiskActivity(): Promise<{ data: Array<{ date: string; risk_events: number; transactions: number }> }> {
    const { data } = await this.client.get('/dashboard/risk-activity');
    return data;
  }

  async getLiveRiskFeed(limit = 10): Promise<{ events: LiveRiskEvent[] }> {
    const { data } = await this.client.get('/dashboard/live-risk-feed', { params: { limit } });
    return data;
  }

  async getRecentTransactions(limit = 20): Promise<{ transactions: RecentTransaction[] }> {
    const { data } = await this.client.get('/dashboard/recent-transactions', { params: { limit } });
    return data;
  }

  // Users
  async getUsers(limit = 50, offset = 0): Promise<{ users: User[]; total: number }> {
    const { data } = await this.client.get('/users', { params: { limit, offset } });
    return data;
  }

  async getUser(userId: number): Promise<User> {
    const { data } = await this.client.get(`/users/${userId}`);
    return data;
  }

  async getUserTrust(userId: number): Promise<TrustScoreResponse> {
    const { data } = await this.client.get(`/users/${userId}/trust`);
    return data;
  }

  async getUserTransactions(userId: number, limit = 50, offset = 0): Promise<{
    transactions: Transaction[];
    total: number;
    flagged_count: number;
  }> {
    const { data } = await this.client.get(`/users/${userId}/transactions`, { params: { limit, offset } });
    return data;
  }

  async getUserPayments(userId: number): Promise<{
    sent: PaymentTransaction[];
    received: PaymentTransaction[];
  }> {
    const { data } = await this.client.get(`/users/${userId}/payments`);
    return data;
  }

  // Risk
  async assessRisk(request: { user_id: number; amount: number; payment_method: string }): Promise<{
    risk_assessment: RiskAssessment;
    user: { id: number; name: string; role: string };
    assessed_amount: number;
    assessed_method: string;
    timestamp: string;
  }> {
    const { data } = await this.client.post('/risk/assess', request);
    return data;
  }

  async getRiskEvents(limit = 50, riskLevel?: string, source?: string): Promise<{
    events: RiskEvent[];
    total: number;
  }> {
    const { data } = await this.client.get('/risk/events', { params: { limit, risk_level: riskLevel, source } });
    return data;
  }

  async getRiskEvent(eventId: number): Promise<any> {
    const { data } = await this.client.get(`/risk/events/${eventId}`);
    return data;
  }

  async getModelEvaluation(): Promise<ModelEvaluation> {
    const { data } = await this.client.get('/risk/evaluation');
    return data;
  }

  async getRuleVsMLComparison(): Promise<RuleVsMLComparison> {
    const { data } = await this.client.get('/risk/comparison');
    return data;
  }

  async explainRiskEvent(transactionId: number): Promise<any> {
    const { data } = await this.client.get(`/risk/explain/${transactionId}`);
    return data;
  }

  // Payments
  async simulatePayment(request: SimulatePaymentRequest): Promise<SimulatePaymentResponse> {
    const { data } = await this.client.post('/payments/simulate', request);
    return data;
  }

  async getPayments(limit = 50, offset = 0, status?: string): Promise<PaymentTransaction[]> {
    const { data } = await this.client.get('/payments', { params: { limit, offset, status } });
    return data;
  }

  async getPayment(paymentId: number): Promise<PaymentTransaction> {
    const { data } = await this.client.get(`/payments/${paymentId}`);
    return data;
  }

  async getPaymentByIdempotencyKey(key: string): Promise<PaymentTransaction> {
    const { data } = await this.client.get(`/payments/by-idempotency/${key}`);
    return data;
  }

  async getPaymentByReference(referenceId: string): Promise<PaymentTransaction> {
    const { data } = await this.client.get(`/payments/by-reference/${referenceId}`);
    return data;
  }

  async getLedgerForPayment(paymentId: number): Promise<LedgerEntry[]> {
    const { data } = await this.client.get(`/ledger/${paymentId}`);
    return data;
  }

  async verifyLedger(paymentId: number): Promise<{
    payment_transaction_id: number;
    total_debits: number;
    total_credits: number;
    is_balanced: boolean;
    entry_count: number;
    entries: Array<{ account_id: number; entry_type: string; amount: number; balance_after: number }>;
  }> {
    const { data } = await this.client.get(`/ledger/${paymentId}/verify`);
    return data;
  }

  async getAccountPayments(accountId: number, limit = 50): Promise<{
    account_id: number;
    sent: Array<{ id: number; reference_id: string; amount: number; status: string; payment_method: string; receiver_account_id: number; created_at: string }>;
    received: Array<{ id: number; reference_id: string; amount: number; status: string; payment_method: string; sender_account_id: number; created_at: string }>;
  }> {
    const { data } = await this.client.get(`/accounts/${accountId}/payments`, { params: { limit } });
    return data;
  }

  // Health
  async healthCheck(): Promise<{ status: string; service: string; version: string }> {
    const { data } = await this.client.get('/health');
    return data;
  }

  // AI Copilot
  async askCopilot(request: CopilotRequest): Promise<CopilotResponse> {
    const { data } = await this.client.post('/copilot/ask', request);
    return data;
  }

  async getCopilotStatus(): Promise<{ available: boolean; provider: string | null; model: string | null; message: string }> {
    const { data } = await this.client.get('/copilot/status');
    return data;
  }

  async getCopilotExamples(): Promise<{ examples: string[]; note: string }> {
    const { data } = await this.client.get('/copilot/examples');
    return data;
  }
}

export const api = new ApiClient();

// React Query hooks
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

export function useDashboardSummary() {
  return useQuery({
    queryKey: ['dashboard', 'summary'],
    queryFn: () => api.getDashboardSummary(),
    refetchInterval: 30000,
  });
}

export function useLiveRiskFeed(limit = 10) {
  return useQuery({
    queryKey: ['dashboard', 'live-risk-feed', limit],
    queryFn: () => api.getLiveRiskFeed(limit),
    refetchInterval: 10000,
  });
}

export function useRecentTransactions(limit = 20) {
  return useQuery({
    queryKey: ['dashboard', 'recent-transactions', limit],
    queryFn: () => api.getRecentTransactions(limit),
    refetchInterval: 30000,
  });
}

export function useUsers(limit = 50, offset = 0) {
  return useQuery({
    queryKey: ['users', { limit, offset }],
    queryFn: () => api.getUsers(limit, offset),
  });
}

export function useUser(userId: number) {
  return useQuery({
    queryKey: ['users', userId],
    queryFn: () => api.getUser(userId),
    enabled: !!userId,
  });
}

export function useUserTrust(userId: number) {
  return useQuery({
    queryKey: ['users', userId, 'trust'],
    queryFn: () => api.getUserTrust(userId),
    enabled: !!userId,
  });
}

export function useUserTransactions(userId: number, limit = 50, offset = 0) {
  return useQuery({
    queryKey: ['users', userId, 'transactions', { limit, offset }],
    queryFn: () => api.getUserTransactions(userId, limit, offset),
    enabled: !!userId,
  });
}

export function useUserPayments(userId: number) {
  return useQuery({
    queryKey: ['users', userId, 'payments'],
    queryFn: () => api.getUserPayments(userId),
    enabled: !!userId,
  });
}

export function useRiskAssessment() {
  return useMutation({
    mutationFn: (request: { user_id: number; amount: number; payment_method: string }) =>
      api.assessRisk(request),
  });
}

export function useRiskEvents(limit = 50, riskLevel?: string, source?: string) {
  return useQuery({
    queryKey: ['risk', 'events', { limit, riskLevel, source }],
    queryFn: () => api.getRiskEvents(limit, riskLevel, source),
    refetchInterval: 30000,
  });
}

export function useRiskEvent(eventId: number) {
  return useQuery({
    queryKey: ['risk', 'events', eventId],
    queryFn: () => api.getRiskEvent(eventId),
    enabled: !!eventId,
  });
}

export function useModelEvaluation() {
  return useQuery({
    queryKey: ['risk', 'evaluation'],
    queryFn: () => api.getModelEvaluation(),
  });
}

export function useRuleVsMLComparison() {
  return useQuery({
    queryKey: ['risk', 'comparison'],
    queryFn: () => api.getRuleVsMLComparison(),
  });
}

export function useExplainRisk(transactionId: number) {
  return useQuery({
    queryKey: ['risk', 'explain', transactionId],
    queryFn: () => api.explainRiskEvent(transactionId),
    enabled: !!transactionId,
  });
}

export function useSimulatePayment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (request: SimulatePaymentRequest) => api.simulatePayment(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['payments'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['risk', 'events'] });
    },
  });
}

export function usePayments(limit = 50, offset = 0, status?: string) {
  return useQuery({
    queryKey: ['payments', { limit, offset, status }],
    queryFn: () => api.getPayments(limit, offset, status),
  });
}

export function usePayment(paymentId: number) {
  return useQuery({
    queryKey: ['payments', paymentId],
    queryFn: () => api.getPayment(paymentId),
    enabled: !!paymentId,
  });
}

export function useLedger(paymentId: number) {
  return useQuery({
    queryKey: ['ledger', paymentId],
    queryFn: () => api.getLedgerForPayment(paymentId),
    enabled: !!paymentId,
  });
}

export function useVerifyLedger(paymentId: number) {
  return useMutation({
    mutationFn: () => api.verifyLedger(paymentId),
  });
}

export function useAccountPayments(accountId: number, limit = 50) {
  return useQuery({
    queryKey: ['accounts', accountId, 'payments', limit],
    queryFn: () => api.getAccountPayments(accountId, limit),
    enabled: !!accountId,
  });
}

export function useAskCopilot() {
  return useMutation({
    mutationFn: (request: CopilotRequest) => api.askCopilot(request),
  });
}

export function useCopilotStatus() {
  return useQuery({
    queryKey: ['copilot', 'status'],
    queryFn: () => api.getCopilotStatus(),
  });
}

export function useCopilotExamples() {
  return useQuery({
    queryKey: ['copilot', 'examples'],
    queryFn: () => api.getCopilotExamples(),
  });
}