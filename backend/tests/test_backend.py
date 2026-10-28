import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.prioritization_engine import evaluate_account_priority

client = TestClient(app)

def test_root_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "operational"
    assert "CredResolve" in data["platform"]

    # Test frontend HTML index serving
    html_resp = client.get("/")
    assert html_resp.status_code == 200
    assert "CredResolve" in html_resp.text

def test_auth_demo_users():
    response = client.get("/api/v1/auth/demo-users")
    assert response.status_code == 200
    users = response.json()
    assert len(users) >= 4
    roles = [u["role"] for u in users]
    assert "admin" in roles
    assert "agent" in roles
    assert "manager" in roles
    assert "auditor" in roles

def test_auth_login_success():
    response = client.post("/api/v1/auth/login", json={
        "email": "admin@credresolve.com",
        "password": "credresolve123"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["role"] == "admin"

def test_auth_login_invalid():
    response = client.post("/api/v1/auth/login", json={
        "email": "admin@credresolve.com",
        "password": "wrongpassword"
    })
    assert response.status_code == 401

def test_auth_google_unconfigured():
    response = client.post("/api/v1/auth/google", json={
        "id_token": "dummy_token"
    })
    # When GOOGLE_CLIENT_ID is not configured, returns 400 with helpful instruction
    assert response.status_code == 400
    assert "Google OAuth is not configured" in response.json()["detail"]

def test_dashboard_summary():
    response = client.get("/api/v1/dashboard/summary")
    assert response.status_code == 200
    data = response.json()
    assert "kpis" in data
    assert "trends" in data
    assert data["kpis"]["total_accounts"] == 30000
    assert data["kpis"]["total_outstanding"] > 0
    assert data["kpis"]["collection_rate_pct"] > 0
    assert len(data["trends"]) > 0

def test_accounts_list():
    response = client.get("/api/v1/accounts?page=1&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 30000
    assert len(data["items"]) == 10
    first = data["items"][0]
    assert "account_id" in first
    assert "priority_score" in first
    assert "priority_tier" in first

def test_borrowers_list():
    response = client.get("/api/v1/borrowers?page=1&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] > 0
    assert len(data["items"]) == 10
    # Test PII masking
    assert "phone_masked" in data["items"][0]
    assert "XXXXX" in data["items"][0]["phone_masked"]

def test_work_queue():
    response = client.get("/api/v1/queue?page=1&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 10
    # Top item should have high score
    assert data["items"][0]["priority_score"] >= data["items"][-1]["priority_score"]

def test_prioritization_engine_scoring():
    # Test high risk account
    high_acc = {
        "dpd": 120,
        "outstanding_amount": 650000.0,
        "risk_segment": "NPA",
        "status": "DELINQUENT",
        "timezone": "Asia/Kolkata"
    }
    report = evaluate_account_priority(high_acc)
    assert report["score"] >= 75.0
    assert report["tier"] == "CRITICAL"
    assert len(report["factors"]) == 5

    # Test compliance hold guardrail
    complaint_acc = {
        "dpd": 45,
        "outstanding_amount": 150000.0,
        "risk_segment": "HIGH",
        "status": "DELINQUENT",
        "timezone": "Asia/Kolkata"
    }
    comp_report = evaluate_account_priority(
        complaint_acc,
        recent_complaints=[{"complaint_type": "HARASSMENT", "severity": "CRITICAL", "status": "OPEN"}]
    )
    assert comp_report["compliance_hold"] is True
    assert "Compliance Pause" in comp_report["recommended_action"]

def test_data_quality_report():
    response = client.get("/api/v1/data-quality/report")
    assert response.status_code == 200
    data = response.json()
    assert data["overall_health_score_pct"] >= 90.0
    assert data["total_raw_rows"] > 500000
    assert data["total_duplicates_purged"] > 25000
    assert len(data["tables"]) >= 10

def test_payments_summary():
    response = client.get("/api/v1/payments/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["total_payments_recorded"] == 25000
    assert data["total_successful_amount"] > 0
    assert data["success_rate_pct"] > 50.0

def test_metric_definitions():
    response = client.get("/api/v1/reports/definitions")
    assert response.status_code == 200
    data = response.json()
    assert "kpi_metrics" in data
    assert "compliance_guardrails" in data
    assert "data_cleaning_decisions" in data

def test_all_four_demo_profiles_authenticate():
    demo_credentials = [
        ("admin@credresolve.com", "admin"),
        ("manager@credresolve.com", "manager"),
        ("agent@credresolve.com", "agent"),
        ("auditor@credresolve.com", "auditor")
    ]
    for email, role in demo_credentials:
        resp = client.post("/api/v1/auth/login", json={
            "email": email,
            "password": "credresolve123"
        })
        assert resp.status_code == 200, f"Failed to login with {email}"
        token_data = resp.json()
        assert token_data["user"]["role"] == role
        assert "access_token" in token_data

        # Verify /auth/me with bearer token
        me_resp = client.get("/api/v1/auth/me", headers={
            "Authorization": f"Bearer {token_data['access_token']}"
        })
        assert me_resp.status_code == 200
        assert me_resp.json()["email"] == email

def test_all_modules_and_endpoints():
    # Campaigns
    c_resp = client.get("/api/v1/campaigns?page=1&page_size=5")
    assert c_resp.status_code == 200
    assert "items" in c_resp.json()

    # Communications Summary and Calls
    comm_resp = client.get("/api/v1/communications/summary")
    assert comm_resp.status_code == 200
    calls_resp = client.get("/api/v1/communications/calls?page=1&page_size=5")
    assert calls_resp.status_code == 200

    # Field Visits
    fv_resp = client.get("/api/v1/field-visits?page=1&page_size=5")
    assert fv_resp.status_code == 200
    assert "items" in fv_resp.json()

    # Complaints Summary
    comp_resp = client.get("/api/v1/complaints/summary")
    assert comp_resp.status_code == 200

    # PTP Summary
    ptp_resp = client.get("/api/v1/ptp/summary")
    assert ptp_resp.status_code == 200

    # Agents
    agent_resp = client.get("/api/v1/agents?page=1&page_size=5")
    assert agent_resp.status_code == 200

def test_csv_export_endpoint():
    resp = client.get("/api/v1/reports/export-csv?report_type=accounts")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "account_id" in resp.text[:100]
