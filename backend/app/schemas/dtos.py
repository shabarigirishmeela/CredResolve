from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# --- Auth Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str
    user: Dict[str, Any]

class LoginRequest(BaseModel):
    email: str
    password: str

class GoogleTokenRequest(BaseModel):
    id_token: str

class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str
    role: str = "agent"

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime

# --- Dashboard Schemas ---
class KPIMetrics(BaseModel):
    total_accounts: int
    total_outstanding: float
    total_principal: float
    overdue_accounts: int
    overdue_outstanding: float
    payments_collected: float
    collection_rate_pct: float
    ptp_rate_pct: float
    ptp_kept_pct: float
    total_complaints: int
    open_complaints: int
    complaint_resolution_rate_pct: float
    high_risk_accounts: int

class TrendPoint(BaseModel):
    date: str
    collected_amount: float
    transaction_count: int
    ptp_created: int
    ptp_kept: int

class ChannelMetric(BaseModel):
    channel: str
    total_outreach: int
    success_count: int
    conversion_rate: float

class DashboardSummaryResponse(BaseModel):
    kpis: KPIMetrics
    trends: List[TrendPoint]
    risk_distribution: Dict[str, int]
    loan_type_distribution: Dict[str, float]
    status_distribution: Dict[str, int]
    complaint_severity_breakdown: Dict[str, int]

# --- Account & Prioritization Schemas ---
class PriorityFactor(BaseModel):
    factor_name: str
    raw_value: Any
    weight: float
    points_awarded: float
    rationale: str

class ExplainabilityReport(BaseModel):
    score: float
    tier: str
    recommended_action: str
    compliance_hold: bool
    compliance_reason: Optional[str] = None
    factors: List[PriorityFactor]
    contact_window_open: bool
    borrower_local_time: str
    timezone: str

class AccountItem(BaseModel):
    account_id: str
    borrower_id: Optional[str]
    borrower_name: Optional[str] = None
    borrower_city: Optional[str] = None
    borrower_state: Optional[str] = None
    loan_type: str
    principal_amount: float
    outstanding_amount: float
    dpd: int
    risk_segment: str
    status: str
    opened_at: Optional[datetime]
    timezone: str
    priority_score: float
    priority_tier: str
    recommended_action: str
    compliance_hold: bool

    model_config = ConfigDict(from_attributes=True)

class WorkQueueItem(AccountItem):
    explainability: Optional[ExplainabilityReport] = None
    last_contact_outcome: Optional[str] = None
    last_contact_date: Optional[datetime] = None
    preferred_channel: Optional[str] = None
    ptp_status: Optional[str] = None
    assigned_agent: Optional[str] = None

# --- Borrower Schemas ---
class BorrowerDetail(BaseModel):
    borrower_id: str
    name: str
    phone: Optional[str]
    email: Optional[str]
    city: Optional[str]
    state: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    is_enriched: bool
    accounts: List[Dict[str, Any]]
    recent_payments: List[Dict[str, Any]]
    recent_contacts: List[Dict[str, Any]]
    complaints: List[Dict[str, Any]]
    ptps: List[Dict[str, Any]]

# --- Data Quality Schemas ---
class TableAudit(BaseModel):
    table_name: str
    raw_rows: int
    clean_rows: int
    duplicates_removed: int
    null_fields: int
    conflicts: int
    cleaning_rule_applied: str

class DataQualityReport(BaseModel):
    overall_health_score_pct: float
    total_raw_rows: int
    total_clean_rows: int
    total_duplicates_purged: int
    total_anomalies_handled: int
    tables: List[TableAudit]
    timestamp_conflicts: int
    missing_foreign_keys_resolved: int
    legacy_codes_mapped: int
    duplicate_payment_references: int

# --- Generic Pagination Response ---
class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int
