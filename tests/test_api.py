import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["track_id"] == "PS6"

def test_list_sample_cases():
    response = client.get("/api/sample-cases")
    assert response.status_code == 200
    data = response.json()
    assert len(data["scenarios"]) == 9

def test_normal_customer_sample_case():
    response = client.get("/api/sample-cases/normal_customer")
    assert response.status_code == 200
    data = response.json()
    report = data["report"]
    assert report["status"] == "NO_ATTENTION_REQUIRED"
    assert report["risk_level"] == "LOW"
    assert len(report["rules_triggered"]) == 0

def test_large_transfer_sample_case():
    response = client.get("/api/sample-cases/large_transfer")
    assert response.status_code == 200
    data = response.json()
    report = data["report"]
    assert report["status"] == "ATTENTION_REQUIRED"
    assert len(report["rules_triggered"]) >= 1

def test_contradictory_data_sample_case():
    response = client.get("/api/sample-cases/contradictory_data")
    assert response.status_code == 200
    data = response.json()
    report = data["report"]
    assert report["status"] == "INVESTIGATOR_REVIEW_REQUIRED"
    assert len(report["contradictions"]) >= 1

def test_insufficient_history_clean_report():
    response = client.get("/api/sample-cases/insufficient_history")
    assert response.status_code == 200
    data = response.json()
    report = data["report"]
    assert report["status"] == "INSUFFICIENT_EVIDENCE"
    assert report["risk_level"] == "UNKNOWN"
    assert len(report["rules_triggered"]) == 0
    assert len(report["priority_transactions"]) == 0
