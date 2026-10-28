export type UserRole = 'admin' | 'manager' | 'agent' | 'auditor';

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
}

export interface DemoUser {
  email: string;
  password: string;
  full_name: string;
  role: UserRole;
  description: string;
}

export interface KPIMetrics {
  total_accounts: number;
  total_outstanding: number;
  total_principal: number;
  overdue_accounts: number;
  overdue_outstanding: number;
  payments_collected: number;
  collection_rate_pct: number;
  ptp_rate_pct: number;
  ptp_kept_pct: number;
  total_complaints: number;
  open_complaints: number;
  complaint_resolution_rate_pct: number;
  high_risk_accounts: number;
}

export interface TrendPoint {
  date: string;
  collected_amount: number;
  transaction_count: number;
  ptp_created: number;
  ptp_kept: number;
}

export interface DashboardData {
  kpis: KPIMetrics;
  trends: TrendPoint[];
  risk_distribution: Record<string, number>;
  loan_type_distribution: Record<string, number>;
  status_distribution: Record<string, number>;
  complaint_severity_breakdown: Record<string, number>;
}

export interface PriorityFactor {
  factor_name: string;
  raw_value: any;
  weight: number;
  points_awarded: number;
  rationale: string;
}

export interface ExplainabilityReport {
  score: number;
  tier: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  recommended_action: string;
  compliance_hold: boolean;
  compliance_reason?: string;
  factors: PriorityFactor[];
  contact_window_open: boolean;
  borrower_local_time: string;
  timezone: string;
}

export interface AccountItem {
  account_id: string;
  borrower_id?: string;
  borrower_name?: string;
  borrower_city?: string;
  borrower_state?: string;
  phone_masked?: string;
  loan_type: string;
  principal_amount: number;
  outstanding_amount: number;
  dpd: number;
  risk_segment: string;
  status: string;
  opened_at?: string;
  timezone: string;
  priority_score: number;
  priority_tier: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  recommended_action: string;
  compliance_hold: boolean;
  compliance_reason?: string;
}

export interface BorrowerItem {
  borrower_id: string;
  name: string;
  phone_masked: string;
  email_masked: string;
  city: string;
  state: string;
  created_at?: string;
  is_enriched: boolean;
  account_count: number;
  total_outstanding: number;
  max_dpd: number;
  max_score: number;
}

export interface PaymentItem {
  payment_id: string;
  account_id: string;
  borrower_id?: string;
  amount: number;
  event_at: string;
  payment_status: 'SUCCESS' | 'FAILED' | 'PENDING' | 'REVERSED';
  payment_method: string;
  payment_reference?: string;
  provider_id?: string;
  is_duplicate_ref: boolean;
}

export interface PTPItem {
  ptp_id: string;
  account_id: string;
  borrower_id?: string;
  agent_id?: string;
  promised_amount: number;
  promised_date: string;
  event_at: string;
  status: 'KEPT' | 'BROKEN' | 'OPEN' | 'CANCELLED';
  source: string;
}

export interface AgentItem {
  agent_id: string;
  employee_code?: string;
  agent_name: string;
  team?: string;
  vendor_id?: string;
  status: string;
  joined_at?: string;
  total_calls: number;
  answered_calls: number;
  contact_rate_pct: number;
  avg_call_duration_sec: number;
  total_ptp_secured: number;
  kept_ptp: number;
  ptp_conversion_rate_pct: number;
  total_promised_amount: number;
}

export interface CampaignItem {
  campaign_id: string;
  campaign_name: string;
  channel: string;
  strategy_version: string;
  start_at?: string;
  end_at?: string;
  target_definition?: string;
  targeted_accounts: number;
  outreach_events: number;
  engagement_rate_pct: number;
}

export interface CallItem {
  call_id: string;
  account_id: string;
  borrower_id?: string;
  agent_id: string;
  campaign_id?: string;
  direction: string;
  call_status: string;
  duration_sec: number;
  event_at: string;
  timezone: string;
}

export interface FieldVisitItem {
  visit_id: string;
  account_id: string;
  borrower_id?: string;
  agent_id?: string;
  agent_name: string;
  visit_type: string;
  outcome: string;
  latitude?: number;
  longitude?: number;
  scheduled_at?: string;
  event_at: string;
}

export interface ComplaintItem {
  complaint_id: string;
  account_id: string;
  borrower_id?: string;
  complaint_type: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  status: 'OPEN' | 'INVESTIGATING' | 'RESOLVED' | 'CLOSED';
  source: string;
  event_at: string;
  resolution_at?: string;
}

export interface TableAudit {
  table_name: string;
  raw_rows: number;
  clean_rows: number;
  duplicates_removed: number;
  null_fields: number;
  conflicts: number;
  cleaning_rule_applied: string;
}

export interface DataQualityReport {
  overall_health_score_pct: number;
  total_raw_rows: number;
  total_clean_rows: number;
  total_duplicates_purged: number;
  total_null_fields_handled: number;
  timestamp_conflicts_detected: number;
  tables_monitored: number;
  tables: TableAudit[];
}

export interface PaginatedResult<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}
