export type ReviewStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'ESCALATED';
export type SeverityLevel = 'LOW' | 'MEDIUM' | 'HIGH';
export type ConfidenceLevel = 'LOW' | 'MEDIUM' | 'HIGH';

export interface HealthStatus {
  status: string;
}

export interface TransactionSummary {
  transaction_id: string;
  status: 'MATCHED' | 'EXCEPTION';
  exception_type: string | null;
  match_score: number;
  recommended_action: string;
  details: Record<string, any>;
}

export interface SourceRecord {
  transaction_id: string;
  source_system: 'payment' | 'bank' | 'ledger' | string;
  amount: string;
  currency: string;
  transaction_date: string | null;
  status: string;
  reference_id: string | null;
  customer_id: string | null;
  order_id: string | null;
}

export interface ReconciliationResult {
  transaction_id: string;
  matched: boolean;
  match_score: number;
  exception_type: string | null;
  explanations: string[];
  recommended_action: string;
  details: Record<string, any>;
}

export interface TransactionDetail {
  transaction_id: string;
  source_records: {
    payment?: SourceRecord;
    bank?: SourceRecord;
    ledger?: SourceRecord;
  };
  normalized_values: {
    payment: string | null;
    bank: string | null;
    ledger: string | null;
  };
  reconciliation_result: ReconciliationResult | null;
}

export interface ReviewHistoryItem {
  previous_state: string;
  new_state: string;
  reviewer: string;
  timestamp: string;
  comment: string;
}

export interface ExceptionItem {
  exception_id: string;
  audit_id: string;
  transaction_id: string;
  exception_type: string;
  severity: SeverityLevel;
  difference: number | null;
  recommended_action: string;
  review_status: ReviewStatus;
  reason: string;
  review_history: ReviewHistoryItem[];
  transaction: TransactionDetail | null;
}

export interface PossibleCause {
  cause: string;
  likelihood: 'HIGH' | 'LOW' | 'MEDIUM' | string;
  reason: string;
}

export interface InvestigationEvidence {
  transaction_id?: string;
  payment_amount?: number | null;
  bank_amount?: number | null;
  ledger_amount?: number | null;
  difference?: number | null;
  similar_transactions?: Array<{ transaction_id: string; difference: number | null }>;
  known_fee_rule?: boolean;
  [key: string]: any;
}

export interface InvestigationResponse {
  investigation_id: string;
  exception_id: string;
  investigation_status: 'COMPLETED' | 'INSUFFICIENT_EVIDENCE' | 'PENDING' | 'INVESTIGATING' | 'FAILED' | string;
  summary: string;
  findings: string[];
  evidence: InvestigationEvidence;
  possible_causes: PossibleCause[];
  most_likely_cause: string;
  confidence: ConfidenceLevel;
  recommended_action: string;
  requires_human_review: boolean;
}

export interface ReviewRequest {
  decision: 'APPROVED' | 'REJECTED' | 'ESCALATED';
  reviewer: string;
  comment: string;
}

export interface ReviewResponse {
  exception_id: string;
  audit_id: string;
  review_status: ReviewStatus;
  review_history: ReviewHistoryItem[];
  reviewer: string;
  comment: string;
}

export interface RawAuditRecord {
  audit_id: string;
  transaction_id: string;
  match_status: string;
  exception_type: string;
  payment_amount: number | null;
  bank_amount: number | null;
  ledger_amount: number | null;
  difference: number | null;
  recommended_action: string;
  review_status: ReviewStatus;
  review_history: ReviewHistoryItem[];
  processing_timestamp: string;
  reviewer?: string;
  reviewer_comment?: string;
  resolution_timestamp?: string;
}

export interface InvestigationSummaryItem {
  investigation_id: string;
  exception_id: string;
  status: string;
  summary: string;
}

export interface AuditHistory {
  transaction_id: string;
  audit_records: RawAuditRecord[];
  exception_information: ExceptionItem[];
  investigations: InvestigationSummaryItem[];
  review_actions: ReviewHistoryItem[];
}

export interface ReconciliationReportResultItem {
  transaction_id: string;
  matched: boolean;
  exception_type: string | null;
  recommended_action: string;
  details: Record<string, any>;
}

export interface ReconciliationReport {
  total_records: number;
  matched: number;
  unresolved: number;
  match_rate: number;
  exception_breakdown: Record<string, number>;
  results: ReconciliationReportResultItem[];
}

export interface ExceptionReport {
  total_records: number;
  matched_records: number;
  exception_count: number;
  unresolved_count: number;
  resolved_count: number;
  match_rate: number;
  resolution_rate: number;
  exception_breakdown: Record<string, number>;
  total_financial_difference: number;
  high_value_unresolved_exceptions: ReconciliationReportResultItem[];
  detailed_exceptions: ReconciliationReportResultItem[];
}
