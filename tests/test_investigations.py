"""
Investigation case API tests for TrustBridge backend.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from backend.main import app
from database.db import get_session_direct, init_db, reset_db
from database.models import User, Account, Transaction, PaymentTransaction, InvestigationCase, AuditLog, CaseStatus, CaseDecision


@pytest.fixture(scope="module")
def client():
    """Create test client with seeded database."""
    reset_db()
    init_db()
    from data.generator import generate_synthetic_data
    generate_synthetic_data()

    from engine.ml_fraud import train_isolation_forest
    train_isolation_forest()

    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="function")
def db_session():
    """Create a database session for tests."""
    from database.db import get_session_direct
    session = get_session_direct()
    try:
        yield session
    finally:
        session.close()


class TestInvestigationEndpoints:
    """Test investigation case endpoints."""

    def _get_txn_id(self, db_session, offset=0):
        """Get a transaction ID at the given offset."""
        txn = db_session.query(Transaction).offset(offset).first()
        if txn:
            return txn.id, "transaction"
        return None, None

    def _get_payment_id(self, db_session, offset=0):
        """Get a payment transaction ID at the given offset."""
        payment = db_session.query(PaymentTransaction).offset(offset).first()
        if payment:
            return payment.id, "payment"
        return None, None

    def test_create_investigation_case_from_transaction(self, client, db_session):
        """Create an investigation case from an existing transaction."""
        txn_id, txn_type = self._get_txn_id(db_session, 0)
        assert txn_id is not None, "No transactions in database"

        response = client.post("/api/investigations", json={
            "risk_event_id": txn_id,
            "risk_event_type": txn_type
        })
        assert response.status_code == 201
        data = response.json()
        assert data["risk_event_id"] == txn_id
        assert data["risk_event_type"] == txn_type
        assert data["status"] == "pending"
        assert data["notes"] is None
        assert data["decision"] is None
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data
        assert data["resolved_at"] is None

    def test_create_investigation_case_from_payment(self, client, db_session):
        """Create an investigation case from an existing payment."""
        payment_id, payment_type = self._get_payment_id(db_session, 0)
        if payment_id is None:
            pytest.skip("No payment transactions available")

        response = client.post("/api/investigations", json={
            "risk_event_id": payment_id,
            "risk_event_type": payment_type
        })
        assert response.status_code == 201
        data = response.json()
        assert data["risk_event_id"] == payment_id
        assert data["risk_event_type"] == payment_type
        assert data["status"] == "pending"

    def test_create_duplicate_case_fails(self, client, db_session):
        """Creating a duplicate case for the same risk event should fail."""
        txn_id, txn_type = self._get_txn_id(db_session, 1)
        assert txn_id is not None

        response1 = client.post("/api/investigations", json={
            "risk_event_id": txn_id,
            "risk_event_type": txn_type
        })
        assert response1.status_code == 201

        response2 = client.post("/api/investigations", json={
            "risk_event_id": txn_id,
            "risk_event_type": txn_type
        })
        assert response2.status_code == 409
        data = response2.json()
        assert "error" in data

    def test_create_case_nonexistent_risk_event_fails(self, client):
        """Creating a case for a non-existent risk event should fail."""
        response = client.post("/api/investigations", json={
            "risk_event_id": 999999,
            "risk_event_type": "transaction"
        })
        assert response.status_code == 404
        data = response.json()
        assert "error" in data

    def test_create_case_invalid_type_fails(self, client):
        """Creating a case with invalid risk event type should fail."""
        response = client.post("/api/investigations", json={
            "risk_event_id": 1,
            "risk_event_type": "invalid_type"
        })
        assert response.status_code in (422, 400, 404)

    def test_get_investigation_case(self, client, db_session):
        """Get an existing investigation case."""
        txn_id, txn_type = self._get_txn_id(db_session, 2)
        assert txn_id is not None

        create_resp = client.post("/api/investigations", json={
            "risk_event_id": txn_id,
            "risk_event_type": txn_type
        })
        assert create_resp.status_code == 201
        case_id = create_resp.json()["id"]

        response = client.get(f"/api/investigations/{case_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == case_id
        assert data["risk_event_id"] == txn_id
        assert data["risk_event_type"] == txn_type
        assert data["status"] == "pending"

    def test_get_nonexistent_case_fails(self, client):
        """Getting a non-existent case should fail."""
        response = client.get("/api/investigations/999999")
        assert response.status_code == 404
        data = response.json()
        assert "error" in data

    def test_update_notes(self, client, db_session):
        """Update investigation case notes."""
        txn_id, txn_type = self._get_txn_id(db_session, 3)
        assert txn_id is not None

        create_resp = client.post("/api/investigations", json={
            "risk_event_id": txn_id,
            "risk_event_type": txn_type
        })
        assert create_resp.status_code == 201
        case_id = create_resp.json()["id"]

        response = client.patch(f"/api/investigations/{case_id}", json={
            "notes": "Reviewed transaction details. Suspicious amount pattern."
        })
        assert response.status_code == 200
        data = response.json()
        assert data["notes"] == "Reviewed transaction details. Suspicious amount pattern."
        assert data["status"] == "pending"

    def test_transition_pending_to_under_review(self, client, db_session):
        """Transition case from pending to under_review."""
        txn_id, txn_type = self._get_txn_id(db_session, 4)
        assert txn_id is not None

        create_resp = client.post("/api/investigations", json={
            "risk_event_id": txn_id,
            "risk_event_type": txn_type
        })
        assert create_resp.status_code == 201
        case_id = create_resp.json()["id"]

        response = client.patch(f"/api/investigations/{case_id}", json={
            "status": "under_review"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "under_review"

    def test_transition_under_review_to_resolved(self, client, db_session):
        """Transition case from under_review to resolved with decision."""
        txn_id, txn_type = self._get_txn_id(db_session, 5)
        assert txn_id is not None

        create_resp = client.post("/api/investigations", json={
            "risk_event_id": txn_id,
            "risk_event_type": txn_type
        })
        assert create_resp.status_code == 201
        case_id = create_resp.json()["id"]

        client.patch(f"/api/investigations/{case_id}", json={"status": "under_review"})

        response = client.patch(f"/api/investigations/{case_id}", json={
            "status": "resolved",
            "decision": "true_positive",
            "notes": "Confirmed fraud pattern."
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "resolved"
        assert data["decision"] == "true_positive"
        assert data["notes"] == "Confirmed fraud pattern."
        assert data["resolved_at"] is not None

    def test_transition_under_review_to_dismissed(self, client, db_session):
        """Transition case from under_review to dismissed."""
        txn_id, txn_type = self._get_txn_id(db_session, 6)
        assert txn_id is not None

        create_resp = client.post("/api/investigations", json={
            "risk_event_id": txn_id,
            "risk_event_type": txn_type
        })
        assert create_resp.status_code == 201
        case_id = create_resp.json()["id"]

        client.patch(f"/api/investigations/{case_id}", json={"status": "under_review"})

        response = client.patch(f"/api/investigations/{case_id}", json={
            "status": "dismissed",
            "decision": "false_positive",
            "notes": "Normal transaction after review."
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "dismissed"
        assert data["decision"] == "false_positive"
        assert data["resolved_at"] is not None

    def test_escalation(self, client, db_session):
        """Escalate a case."""
        txn_id, txn_type = self._get_txn_id(db_session, 7)
        assert txn_id is not None

        create_resp = client.post("/api/investigations", json={
            "risk_event_id": txn_id,
            "risk_event_type": txn_type
        })
        assert create_resp.status_code == 201
        case_id = create_resp.json()["id"]

        response = client.patch(f"/api/investigations/{case_id}", json={
            "status": "escalated",
            "decision": "escalated",
            "notes": "Requires senior analyst review."
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "escalated"
        assert data["decision"] == "escalated"
        # escalated is no longer a terminal state - resolved_at should be None
        assert data["resolved_at"] is None

    def test_invalid_transition_fails(self, client, db_session):
        """Invalid state transitions should fail."""
        txn_id, txn_type = self._get_txn_id(db_session, 8)
        assert txn_id is not None

        create_resp = client.post("/api/investigations", json={
            "risk_event_id": txn_id,
            "risk_event_type": txn_type
        })
        assert create_resp.status_code == 201
        case_id = create_resp.json()["id"]

        response = client.patch(f"/api/investigations/{case_id}", json={
            "status": "resolved"
        })
        assert response.status_code == 400
        data = response.json()
        assert "error" in data

    def test_no_transition_from_terminal_states(self, client, db_session):
        """Terminal states should not allow further transitions."""
        txn_id, txn_type = self._get_txn_id(db_session, 9)
        assert txn_id is not None

        create_resp = client.post("/api/investigations", json={
            "risk_event_id": txn_id,
            "risk_event_type": txn_type
        })
        assert create_resp.status_code == 201
        case_id = create_resp.json()["id"]

        client.patch(f"/api/investigations/{case_id}", json={"status": "under_review"})
        client.patch(f"/api/investigations/{case_id}", json={
            "status": "resolved",
            "decision": "true_positive"
        })

        response = client.patch(f"/api/investigations/{case_id}", json={
            "status": "under_review"
        })
        assert response.status_code == 400

    def test_invalid_payload_returns_validation_error(self, client):
        """Invalid payload should return validation error."""
        response = client.post("/api/investigations", json={})
        assert response.status_code == 422

        response = client.post("/api/investigations", json={
            "risk_event_id": 1,
            "risk_event_type": "invalid"
        })
        assert response.status_code in (422, 400)

    def test_audit_log_creation(self, client, db_session):
        """Audit log entry should be created on case creation."""
        txn_id, txn_type = self._get_txn_id(db_session, 10)
        assert txn_id is not None

        create_resp = client.post("/api/investigations", json={
            "risk_event_id": txn_id,
            "risk_event_type": txn_type
        })
        assert create_resp.status_code == 201
        case_id = create_resp.json()["id"]

        response = client.get(f"/api/investigations/{case_id}/audit-log")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

        created_entry = data[0]
        assert created_entry["action"] == "case_created"
        assert created_entry["case_id"] == case_id
        import json
        new_state = json.loads(created_entry["new_state"]) if isinstance(created_entry["new_state"], str) else created_entry["new_state"]
        assert new_state["status"] == "pending"

    def test_audit_log_records_state_changes(self, client, db_session):
        """Audit log should record state changes."""
        txn_id, txn_type = self._get_txn_id(db_session, 11)
        assert txn_id is not None

        create_resp = client.post("/api/investigations", json={
            "risk_event_id": txn_id,
            "risk_event_type": txn_type
        })
        assert create_resp.status_code == 201
        case_id = create_resp.json()["id"]

        client.patch(f"/api/investigations/{case_id}", json={
            "notes": "Initial review"
        })

        client.patch(f"/api/investigations/{case_id}", json={
            "status": "under_review"
        })

        response = client.get(f"/api/investigations/{case_id}/audit-log")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 3

        actions = [entry["action"] for entry in data]
        assert "case_updated" in actions

    def test_audit_log_chronological_order(self, client, db_session):
        """Audit log entries should be in chronological order."""
        txn_id, txn_type = self._get_txn_id(db_session, 12)
        assert txn_id is not None

        create_resp = client.post("/api/investigations", json={
            "risk_event_id": txn_id,
            "risk_event_type": txn_type
        })
        assert create_resp.status_code == 201
        case_id = create_resp.json()["id"]

        client.patch(f"/api/investigations/{case_id}", json={"notes": "First note"})
        client.patch(f"/api/investigations/{case_id}", json={"notes": "Second note"})

        response = client.get(f"/api/investigations/{case_id}/audit-log")
        assert response.status_code == 200
        data = response.json()

        timestamps = [entry["timestamp"] for entry in data]
        assert timestamps == sorted(timestamps)

    def test_audit_log_nonexistent_case_fails(self, client):
        """Getting audit log for non-existent case should fail."""
        response = client.get("/api/investigations/999999/audit-log")
        assert response.status_code == 404

    def test_resolved_timestamp_behavior(self, client, db_session):
        """Resolved timestamp should be set when reaching terminal state."""
        txn_id, txn_type = self._get_txn_id(db_session, 13)
        assert txn_id is not None

        create_resp = client.post("/api/investigations", json={
            "risk_event_id": txn_id,
            "risk_event_type": txn_type
        })
        assert create_resp.status_code == 201
        case_id = create_resp.json()["id"]

        response = client.get(f"/api/investigations/{case_id}")
        assert response.json()["resolved_at"] is None

        client.patch(f"/api/investigations/{case_id}", json={"status": "under_review"})
        response = client.patch(f"/api/investigations/{case_id}", json={
            "status": "resolved",
            "decision": "true_positive"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["resolved_at"] is not None

        txn_id2, txn_type2 = self._get_txn_id(db_session, 14)
        if txn_id2:
            create_resp2 = client.post("/api/investigations", json={
                "risk_event_id": txn_id2,
                "risk_event_type": txn_type2
            })
            case_id2 = create_resp2.json()["id"]
            client.patch(f"/api/investigations/{case_id2}", json={"status": "under_review"})
            response2 = client.patch(f"/api/investigations/{case_id2}", json={
                "status": "dismissed",
                "decision": "false_positive"
            })
            assert response2.status_code == 200
            assert response2.json()["resolved_at"] is not None

    def test_partial_update_works(self, client, db_session):
        """Partial updates should work (only providing some fields)."""
        txn_id, txn_type = self._get_txn_id(db_session, 15)
        assert txn_id is not None

        create_resp = client.post("/api/investigations", json={
            "risk_event_id": txn_id,
            "risk_event_type": txn_type
        })
        assert create_resp.status_code == 201
        case_id = create_resp.json()["id"]

        response = client.patch(f"/api/investigations/{case_id}", json={
            "notes": "Only updating notes"
        })
        assert response.status_code == 200
        assert response.json()["notes"] == "Only updating notes"
        assert response.json()["status"] == "pending"

        response = client.patch(f"/api/investigations/{case_id}", json={
            "status": "under_review"
        })
        assert response.status_code == 200
        assert response.json()["status"] == "under_review"
        assert response.json()["notes"] == "Only updating notes"

    def test_empty_patch_fails(self, client, db_session):
        """Empty patch request should fail."""
        txn_id, txn_type = self._get_txn_id(db_session, 16)
        assert txn_id is not None

        create_resp = client.post("/api/investigations", json={
            "risk_event_id": txn_id,
            "risk_event_type": txn_type
        })
        assert create_resp.status_code == 201
        case_id = create_resp.json()["id"]

        response = client.patch(f"/api/investigations/{case_id}", json={})
        assert response.status_code == 400
        data = response.json()
        assert "error" in data

    def test_resolved_without_decision_rejected(self, client, db_session):
        """Resolved status requires a decision."""
        txn_id, txn_type = self._get_txn_id(db_session, 17)
        assert txn_id is not None

        create_resp = client.post("/api/investigations", json={
            "risk_event_id": txn_id,
            "risk_event_type": txn_type
        })
        assert create_resp.status_code == 201
        case_id = create_resp.json()["id"]

        # First move to under_review
        client.patch(f"/api/investigations/{case_id}", json={"status": "under_review"})

        # Try to resolve without decision
        response = client.patch(f"/api/investigations/{case_id}", json={
            "status": "resolved"
        })
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "Decision is required" in data["error"]

    def test_resolved_with_true_positive_accepted(self, client, db_session):
        """Resolved with true_positive decision should be accepted."""
        txn_id, txn_type = self._get_txn_id(db_session, 18)
        assert txn_id is not None

        create_resp = client.post("/api/investigations", json={
            "risk_event_id": txn_id,
            "risk_event_type": txn_type
        })
        assert create_resp.status_code == 201
        case_id = create_resp.json()["id"]

        client.patch(f"/api/investigations/{case_id}", json={"status": "under_review"})
        response = client.patch(f"/api/investigations/{case_id}", json={
            "status": "resolved",
            "decision": "true_positive",
            "notes": "Confirmed fraud."
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "resolved"
        assert data["decision"] == "true_positive"
        assert data["resolved_at"] is not None

    def test_resolved_with_false_positive_accepted(self, client, db_session):
        """Resolved with false_positive decision should be accepted."""
        txn_id, txn_type = self._get_txn_id(db_session, 19)
        assert txn_id is not None

        create_resp = client.post("/api/investigations", json={
            "risk_event_id": txn_id,
            "risk_event_type": txn_type
        })
        assert create_resp.status_code == 201
        case_id = create_resp.json()["id"]

        client.patch(f"/api/investigations/{case_id}", json={"status": "under_review"})
        response = client.patch(f"/api/investigations/{case_id}", json={
            "status": "resolved",
            "decision": "false_positive",
            "notes": "False alarm."
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "resolved"
        assert data["decision"] == "false_positive"
        assert data["resolved_at"] is not None

    def test_resolved_with_inconclusive_accepted(self, client, db_session):
        """Resolved with inconclusive decision should be accepted."""
        txn_id, txn_type = self._get_txn_id(db_session, 20)
        assert txn_id is not None

        create_resp = client.post("/api/investigations", json={
            "risk_event_id": txn_id,
            "risk_event_type": txn_type
        })
        assert create_resp.status_code == 201
        case_id = create_resp.json()["id"]

        client.patch(f"/api/investigations/{case_id}", json={"status": "under_review"})
        response = client.patch(f"/api/investigations/{case_id}", json={
            "status": "resolved",
            "decision": "inconclusive",
            "notes": "Insufficient evidence."
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "resolved"
        assert data["decision"] == "inconclusive"
        assert data["resolved_at"] is not None

    def test_escalated_with_true_positive_rejected(self, client, db_session):
        """Escalated status with true_positive decision should be rejected."""
        txn_id, txn_type = self._get_txn_id(db_session, 21)
        assert txn_id is not None

        create_resp = client.post("/api/investigations", json={
            "risk_event_id": txn_id,
            "risk_event_type": txn_type
        })
        assert create_resp.status_code == 201
        case_id = create_resp.json()["id"]

        response = client.patch(f"/api/investigations/{case_id}", json={
            "status": "escalated",
            "decision": "true_positive"
        })
        assert response.status_code == 400
        data = response.json()
        assert "error" in data

    def test_escalated_with_false_positive_rejected(self, client, db_session):
        """Escalated status with false_positive decision should be rejected."""
        txn_id, txn_type = self._get_txn_id(db_session, 22)
        assert txn_id is not None

        create_resp = client.post("/api/investigations", json={
            "risk_event_id": txn_id,
            "risk_event_type": txn_type
        })
        assert create_resp.status_code == 201
        case_id = create_resp.json()["id"]

        response = client.patch(f"/api/investigations/{case_id}", json={
            "status": "escalated",
            "decision": "false_positive"
        })
        assert response.status_code == 400
        data = response.json()
        assert "error" in data

    def test_escalated_with_escalated_decision_accepted(self, client, db_session):
        """Escalated status with escalated decision should be accepted."""
        txn_id, txn_type = self._get_txn_id(db_session, 23)
        assert txn_id is not None

        create_resp = client.post("/api/investigations", json={
            "risk_event_id": txn_id,
            "risk_event_type": txn_type
        })
        assert create_resp.status_code == 201
        case_id = create_resp.json()["id"]

        response = client.patch(f"/api/investigations/{case_id}", json={
            "status": "escalated",
            "decision": "escalated",
            "notes": "Escalated to senior team."
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "escalated"
        assert data["decision"] == "escalated"
        # escalated is not terminal - resolved_at should be None
        assert data["resolved_at"] is None

    def test_escalated_to_resolved_accepted(self, client, db_session):
        """Escalated case can transition to resolved."""
        txn_id, txn_type = self._get_txn_id(db_session, 24)
        assert txn_id is not None

        create_resp = client.post("/api/investigations", json={
            "risk_event_id": txn_id,
            "risk_event_type": txn_type
        })
        assert create_resp.status_code == 201
        case_id = create_resp.json()["id"]

        # Escalate first
        client.patch(f"/api/investigations/{case_id}", json={
            "status": "escalated",
            "decision": "escalated"
        })

        # Then resolve
        response = client.patch(f"/api/investigations/{case_id}", json={
            "status": "resolved",
            "decision": "true_positive",
            "notes": "Senior analyst confirmed fraud."
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "resolved"
        assert data["decision"] == "true_positive"
        assert data["resolved_at"] is not None

    def test_escalated_to_dismissed_accepted(self, client, db_session):
        """Escalated case can transition to dismissed."""
        txn_id, txn_type = self._get_txn_id(db_session, 25)
        assert txn_id is not None

        create_resp = client.post("/api/investigations", json={
            "risk_event_id": txn_id,
            "risk_event_type": txn_type
        })
        assert create_resp.status_code == 201
        case_id = create_resp.json()["id"]

        # Escalate first
        client.patch(f"/api/investigations/{case_id}", json={
            "status": "escalated",
            "decision": "escalated"
        })

        # Then dismiss
        response = client.patch(f"/api/investigations/{case_id}", json={
            "status": "dismissed",
            "decision": "false_positive",
            "notes": "False alarm after escalation review."
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "dismissed"
        assert data["decision"] == "false_positive"
        assert data["resolved_at"] is not None

    def test_resolved_transition_blocked(self, client, db_session):
        """Resolved case cannot transition to any other state."""
        txn_id, txn_type = self._get_txn_id(db_session, 26)
        assert txn_id is not None

        create_resp = client.post("/api/investigations", json={
            "risk_event_id": txn_id,
            "risk_event_type": txn_type
        })
        assert create_resp.status_code == 201
        case_id = create_resp.json()["id"]

        client.patch(f"/api/investigations/{case_id}", json={"status": "under_review"})
        client.patch(f"/api/investigations/{case_id}", json={
            "status": "resolved",
            "decision": "true_positive"
        })

        # Try to transition from resolved
        response = client.patch(f"/api/investigations/{case_id}", json={
            "status": "under_review"
        })
        assert response.status_code == 400
        data = response.json()
        assert "error" in data

    def test_dismissed_transition_blocked(self, client, db_session):
        """Dismissed case cannot transition to any other state."""
        txn_id, txn_type = self._get_txn_id(db_session, 27)
        assert txn_id is not None

        create_resp = client.post("/api/investigations", json={
            "risk_event_id": txn_id,
            "risk_event_type": txn_type
        })
        assert create_resp.status_code == 201
        case_id = create_resp.json()["id"]

        client.patch(f"/api/investigations/{case_id}", json={"status": "under_review"})
        client.patch(f"/api/investigations/{case_id}", json={
            "status": "dismissed",
            "decision": "false_positive"
        })

        # Try to transition from dismissed
        response = client.patch(f"/api/investigations/{case_id}", json={
            "status": "under_review"
        })
        assert response.status_code == 400
        data = response.json()
        assert "error" in data

    def test_under_review_to_pending_accepted(self, client, db_session):
        """Under review can transition back to pending."""
        txn_id, txn_type = self._get_txn_id(db_session, 28)
        assert txn_id is not None

        create_resp = client.post("/api/investigations", json={
            "risk_event_id": txn_id,
            "risk_event_type": txn_type
        })
        assert create_resp.status_code == 201
        case_id = create_resp.json()["id"]

        client.patch(f"/api/investigations/{case_id}", json={"status": "under_review"})

        # Transition back to pending
        response = client.patch(f"/api/investigations/{case_id}", json={
            "status": "pending"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"
