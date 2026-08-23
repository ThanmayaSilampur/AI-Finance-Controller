import {
  AuditHistory,
  ExceptionItem,
  ExceptionReport,
  HealthStatus,
  InvestigationResponse,
  ReconciliationReport,
  ReviewHistoryItem,
  ReviewRequest,
  ReviewResponse,
  TransactionDetail,
  TransactionSummary,
} from './types';

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');

export class ApiError extends Error {
  status: number;
  code?: string;
  details?: any;

  constructor(message: string, status: number, code?: string, details?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  timeoutMs: number = 10000
): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
        ...(options.headers || {}),
      },
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      let errorMessage = `HTTP error ${response.status}: ${response.statusText}`;
      let errorCode: string | undefined;
      let errorDetails: any;

      try {
        const errorJson = await response.json();
        errorDetails = errorJson;
        if (errorJson.detail) {
          if (typeof errorJson.detail === 'object') {
            errorMessage = errorJson.detail.message || JSON.stringify(errorJson.detail);
            errorCode = errorJson.detail.error;
          } else {
            errorMessage = String(errorJson.detail);
          }
        } else if (errorJson.message) {
          errorMessage = errorJson.message;
          errorCode = errorJson.error;
        }
      } catch {
        // Fall back to status text if body is not JSON
      }

      throw new ApiError(errorMessage, response.status, errorCode, errorDetails);
    }

    return (await response.json()) as T;
  } catch (err: any) {
    clearTimeout(timeoutId);
    if (err.name === 'AbortError') {
      throw new ApiError('Request timed out while contacting the server.', 408, 'TIMEOUT');
    }
    if (err instanceof ApiError) {
      throw err;
    }
    throw new ApiError(
      err.message || 'Unable to connect to the Finance Controller API.',
      0,
      'NETWORK_ERROR'
    );
  }
}

export const api = {
  // Health
  async getHealth(): Promise<HealthStatus> {
    return request<HealthStatus>('/health');
  },

  // Transactions
  async getTransactions(params?: {
    status?: string;
    exception_type?: string;
    transaction_id?: string;
  }): Promise<TransactionSummary[]> {
    const query = new URLSearchParams();
    if (params?.status) query.set('status', params.status);
    if (params?.exception_type) query.set('exception_type', params.exception_type);
    if (params?.transaction_id) query.set('transaction_id', params.transaction_id);
    const qs = query.toString() ? `?${query.toString()}` : '';
    return request<TransactionSummary[]>(`/transactions${qs}`);
  },

  async getTransaction(transactionId: string): Promise<TransactionDetail> {
    return request<TransactionDetail>(`/transactions/${encodeURIComponent(transactionId)}`);
  },

  // Exceptions
  async getExceptions(params?: {
    exception_type?: string;
    review_status?: string;
    severity?: string;
  }): Promise<ExceptionItem[]> {
    const query = new URLSearchParams();
    if (params?.exception_type) query.set('exception_type', params.exception_type);
    if (params?.review_status) query.set('review_status', params.review_status);
    if (params?.severity) query.set('severity', params.severity);
    const qs = query.toString() ? `?${query.toString()}` : '';
    return request<ExceptionItem[]>(`/exceptions${qs}`);
  },

  async getException(exceptionId: string): Promise<ExceptionItem> {
    return request<ExceptionItem>(`/exceptions/${encodeURIComponent(exceptionId)}`);
  },

  async investigateException(exceptionId: string): Promise<InvestigationResponse> {
    return request<InvestigationResponse>(`/exceptions/${encodeURIComponent(exceptionId)}/investigate`, {
      method: 'POST',
    });
  },

  async reviewException(exceptionId: string, payload: ReviewRequest): Promise<ReviewResponse> {
    return request<ReviewResponse>(`/exceptions/${encodeURIComponent(exceptionId)}/review`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async getExceptionReviews(exceptionId: string): Promise<ReviewHistoryItem[]> {
    return request<ReviewHistoryItem[]>(`/exceptions/${encodeURIComponent(exceptionId)}/reviews`);
  },

  // Audit
  async getAuditHistory(transactionId: string): Promise<AuditHistory> {
    return request<AuditHistory>(`/audit/${encodeURIComponent(transactionId)}`);
  },

  // Reports
  async getReconciliationReport(): Promise<ReconciliationReport> {
    return request<ReconciliationReport>('/reports/reconciliation');
  },

  async getExceptionReport(): Promise<ExceptionReport> {
    return request<ExceptionReport>('/reports/exceptions');
  },

  // Export triggers
  async exportExceptions(format: 'json' | 'csv'): Promise<void> {
    const url = `${API_BASE_URL}/reports/exceptions/export?format=${format}`;
    const response = await fetch(url);
    if (!response.ok) {
      throw new ApiError(`Export failed with HTTP ${response.status}`, response.status);
    }
    const blob = await response.blob();
    const blobUrl = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = blobUrl;
    link.download = `exceptions_report_${new Date().toISOString().slice(0, 10)}.${format}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(blobUrl);
  },
};
