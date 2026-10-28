from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Text, Index
from app.core.database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(120), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(120), nullable=False)
    role = Column(String(50), default="agent", nullable=False)  # admin, manager, agent, auditor
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Borrower(Base):
    __tablename__ = "borrowers"

    borrower_id = Column(String(64), primary_key=True, index=True)
    name = Column(String(150), index=True)
    phone = Column(String(50), index=True, nullable=True)
    email = Column(String(150), nullable=True)
    city = Column(String(100), index=True, nullable=True)
    state = Column(String(100), index=True, nullable=True)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    is_enriched = Column(Boolean, default=True)

class Account(Base):
    __tablename__ = "accounts"

    account_id = Column(String(64), primary_key=True, index=True)
    borrower_id = Column(String(64), index=True, nullable=True)
    loan_type = Column(String(50), index=True)
    principal_amount = Column(Float, default=0.0)
    outstanding_amount = Column(Float, default=0.0, index=True)
    dpd = Column(Integer, default=0, index=True)
    risk_segment = Column(String(50), index=True)
    status = Column(String(50), index=True)  # ACTIVE, DELINQUENT, CLOSED, PAID, WRITEOFF
    opened_at = Column(DateTime, nullable=True)
    timezone = Column(String(50), default="UTC")
    schema_version = Column(String(20), default="v1")

    # Priority score fields for rapid retrieval
    priority_score = Column(Float, default=0.0, index=True)
    priority_tier = Column(String(20), default="LOW", index=True)  # CRITICAL, HIGH, MEDIUM, LOW
    recommended_action = Column(String(100), default="Monitor Account")
    compliance_hold = Column(Boolean, default=False, index=True)
    compliance_reason = Column(String(255), nullable=True)
    explainability_json = Column(Text, nullable=True)

class Agent(Base):
    __tablename__ = "agents"

    agent_id = Column(String(64), primary_key=True, index=True)
    employee_code = Column(String(64), index=True, nullable=True)
    agent_name = Column(String(150), index=True)
    vendor_id = Column(String(64), index=True, nullable=True)
    team = Column(String(50), index=True, nullable=True)
    status = Column(String(50), index=True)  # ACTIVE, INACTIVE, SUSPENDED
    joined_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)

class AgentSession(Base):
    __tablename__ = "agent_sessions"

    session_id = Column(String(64), primary_key=True, index=True)
    agent_id = Column(String(64), index=True)
    login_at = Column(DateTime, index=True)
    channel = Column(String(50))
    device_id = Column(String(64), nullable=True)
    timezone = Column(String(50), default="UTC")
    logout_at = Column(DateTime, nullable=True)

class Campaign(Base):
    __tablename__ = "campaigns"

    campaign_id = Column(String(64), primary_key=True, index=True)
    campaign_name = Column(String(150), index=True)
    channel = Column(String(50), index=True)
    strategy_version = Column(String(50))
    start_at = Column(DateTime, nullable=True)
    target_definition = Column(String(100), nullable=True)
    end_at = Column(DateTime, nullable=True)

class DailyTargeting(Base):
    __tablename__ = "daily_targeting"

    target_id = Column(String(64), primary_key=True, index=True)
    account_id = Column(String(64), index=True)
    campaign_id = Column(String(64), index=True)
    target_date = Column(DateTime, index=True)
    priority = Column(Integer, default=1)
    recommended_channel = Column(String(50))
    status = Column(String(50), index=True)

class Call(Base):
    __tablename__ = "calls"

    call_id = Column(String(64), primary_key=True, index=True)
    account_id = Column(String(64), index=True)
    borrower_id = Column(String(64), index=True, nullable=True)
    event_at = Column(DateTime, index=True)
    agent_id = Column(String(64), index=True, nullable=True)
    campaign_id = Column(String(64), index=True, nullable=True)
    direction = Column(String(20), default="OUTBOUND")
    vendor_id = Column(String(64), nullable=True)
    call_status = Column(String(50), index=True)  # ANSWERED, NO_ANSWER, BUSY, FAILED, VOICEMAIL
    duration_sec = Column(Integer, default=0)
    timezone = Column(String(50), default="UTC")

class CallAttempt(Base):
    __tablename__ = "call_attempts"

    attempt_id = Column(String(64), primary_key=True, index=True)
    account_id = Column(String(64), index=True)
    borrower_id = Column(String(64), index=True, nullable=True)
    event_at = Column(DateTime, index=True)
    call_id = Column(String(64), index=True, nullable=True)
    agent_id = Column(String(64), index=True, nullable=True)
    attempt_no = Column(Integer, default=1)
    vendor_id = Column(String(64), nullable=True)
    attempt_status = Column(String(50), index=True)

class CallDisposition(Base):
    __tablename__ = "call_dispositions"

    disposition_id = Column(String(64), primary_key=True, index=True)
    account_id = Column(String(64), index=True)
    borrower_id = Column(String(64), index=True, nullable=True)
    event_at = Column(DateTime, index=True)
    call_id = Column(String(64), index=True, nullable=True)
    agent_id = Column(String(64), index=True, nullable=True)
    disposition_code = Column(String(50), index=True)  # Normalized PTP, CALLBACK, etc.
    disposition_version = Column(String(20), default="v2")

class Payment(Base):
    __tablename__ = "payments"

    payment_id = Column(String(64), primary_key=True, index=True)
    account_id = Column(String(64), index=True)
    borrower_id = Column(String(64), index=True, nullable=True)
    event_at = Column(DateTime, index=True)
    payment_reference = Column(String(100), index=True, nullable=True)
    amount = Column(Float, default=0.0)
    payment_status = Column(String(50), index=True)  # SUCCESS, FAILED, PENDING, REVERSED
    payment_method = Column(String(50), index=True)  # CARD, UPI, NETBANKING, etc.
    provider_id = Column(String(64), nullable=True)
    is_duplicate_ref = Column(Boolean, default=False, index=True)

class PromiseToPay(Base):
    __tablename__ = "promises_to_pay"

    ptp_id = Column(String(64), primary_key=True, index=True)
    account_id = Column(String(64), index=True)
    borrower_id = Column(String(64), index=True, nullable=True)
    event_at = Column(DateTime, index=True)
    agent_id = Column(String(64), index=True, nullable=True)
    promised_amount = Column(Float, default=0.0)
    promised_date = Column(DateTime, index=True)
    status = Column(String(50), index=True)  # KEPT, BROKEN, OPEN, CANCELLED
    source = Column(String(50), index=True)  # CALL, FIELD, SMS, WHATSAPP

class FieldVisit(Base):
    __tablename__ = "field_visits"

    visit_id = Column(String(64), primary_key=True, index=True)
    account_id = Column(String(64), index=True)
    borrower_id = Column(String(64), index=True, nullable=True)
    event_at = Column(DateTime, index=True)
    agent_id = Column(String(64), index=True, nullable=True)
    visit_type = Column(String(50), index=True)  # FIRST_VISIT, FOLLOWUP, NOTICE, AFTER_HOURS
    outcome = Column(String(50), index=True)     # PAID, PTP, CONTACTED, NOT_AVAILABLE, REFUSED, WRONG_ADDRESS
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    scheduled_at = Column(DateTime, nullable=True)

class Complaint(Base):
    __tablename__ = "complaints"

    complaint_id = Column(String(64), primary_key=True, index=True)
    account_id = Column(String(64), index=True)
    borrower_id = Column(String(64), index=True, nullable=True)
    event_at = Column(DateTime, index=True)
    complaint_type = Column(String(50), index=True)  # HARASSMENT, DISPUTE, PRIVACY, DND, etc.
    severity = Column(String(50), index=True)        # CRITICAL, HIGH, MEDIUM, LOW
    status = Column(String(50), index=True)          # OPEN, INVESTIGATING, RESOLVED, CLOSED
    source = Column(String(50), index=True)          # CALL, FIELD, etc.
    resolution_at = Column(DateTime, nullable=True)

class SmsEvent(Base):
    __tablename__ = "sms_events"

    sms_event_id = Column(String(64), primary_key=True, index=True)
    account_id = Column(String(64), index=True)
    borrower_id = Column(String(64), index=True, nullable=True)
    event_at = Column(DateTime, index=True)
    message_id = Column(String(64), index=True)
    event_type = Column(String(50), index=True)      # SENT, DELIVERED, CLICKED, FAILED
    template_code = Column(String(50), index=True)
    provider_id = Column(String(64), nullable=True)

class WhatsappEvent(Base):
    __tablename__ = "whatsapp_events"

    whatsapp_event_id = Column(String(64), primary_key=True, index=True)
    account_id = Column(String(64), index=True)
    borrower_id = Column(String(64), index=True, nullable=True)
    event_at = Column(DateTime, index=True)
    message_id = Column(String(64), index=True)
    event_type = Column(String(50), index=True)      # SENT, DELIVERED, READ, REPLIED, PAYMENT_CLICK, FAILED
    template_code = Column(String(50), index=True)
    provider_id = Column(String(64), nullable=True)

class VendorTelephony(Base):
    __tablename__ = "vendor_telephony"

    vendor_id = Column(String(64), primary_key=True, index=True)
    vendor_name = Column(String(100))
    vendor_account_id = Column(String(100))
    timezone = Column(String(50), default="UTC")
    status = Column(String(50))
    schema_version = Column(String(20), default="v3")

class AccountStatusHistory(Base):
    __tablename__ = "account_status_history"

    history_id = Column(String(64), primary_key=True, index=True)
    account_id = Column(String(64), index=True)
    borrower_id = Column(String(64), index=True, nullable=True)
    event_at = Column(DateTime, index=True)
    status = Column(String(50), index=True)
    changed_by = Column(String(64), nullable=True)
    source = Column(String(50), nullable=True)
    recorded_at = Column(DateTime, nullable=True)

class DataQualityLog(Base):
    __tablename__ = "data_quality_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    table_name = Column(String(100), index=True)
    raw_rows = Column(Integer, default=0)
    clean_rows = Column(Integer, default=0)
    duplicates_removed = Column(Integer, default=0)
    null_fields_count = Column(Integer, default=0)
    conflicts_detected = Column(Integer, default=0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
