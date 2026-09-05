from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timezone
import json

from backend.schemas.risk import (
    InvestigationCaseCreate,
    InvestigationCaseUpdate,
    InvestigationCaseResponse,
    AuditLogResponse,
    CaseStatus,
    CaseDecision,
    RiskEventType,
)
from backend.db import get_db_session_direct
from database.models import User, Transaction, PaymentTransaction, InvestigationCase, AuditLog, CaseStatus as ModelCaseStatus, CaseDecision as ModelCaseDecision

router = APIRouter()


def get_db():
    db = get_db_session_direct()
    try:
        yield db
    finally:
        db.close()


def _validate_risk_event_exists(db: Session, risk_event_id: int, risk_event_type: RiskEventType) -> bool:
    """Validate that the referenced risk event exists."""
    if risk_event_type == RiskEventType.TRANSACTION:
        return db.query(Transaction).filter(Transaction.id == risk_event_id).first() is not None
    elif risk_event_type == RiskEventType.PAYMENT:
        return db.query(PaymentTransaction).filter(PaymentTransaction.id == risk_event_id).first() is not None
    return False


def _get_risk_event_type_str(db: Session, risk_event_id: int) -> Optional[str]:
    """Determine the risk event type by checking which table has the ID."""
    txn = db.query(Transaction).filter(Transaction.id == risk_event_id).first()
    if txn:
        return "transaction"
    payment = db.query(PaymentTransaction).filter(PaymentTransaction.id == risk_event_id).first()
    if payment:
        return "payment"
    return None


def _create_audit_log(db: Session, case: InvestigationCase, user_id: Optional[int], action: str, old_state: Optional[dict], new_state: Optional[dict]):
    """Create an audit log entry."""
    audit_log = AuditLog(
        case_id=case.id,
        user_id=user_id,
        action=action,
        old_state=json.dumps(old_state) if old_state else None,
        new_state=json.dumps(new_state) if new_state else None,
        timestamp=datetime.now(timezone.utc),
    )
    db.add(audit_log)
    db.flush()


def _validate_transition(current_status: ModelCaseStatus, new_status: ModelCaseStatus) -> bool:
    """Validate state transitions."""
    valid_transitions = {
        ModelCaseStatus.PENDING: {ModelCaseStatus.UNDER_REVIEW, ModelCaseStatus.DISMISSED, ModelCaseStatus.ESCALATED},
        ModelCaseStatus.UNDER_REVIEW: {ModelCaseStatus.RESOLVED, ModelCaseStatus.DISMISSED, ModelCaseStatus.ESCALATED, ModelCaseStatus.PENDING},
        ModelCaseStatus.RESOLVED: set(),
        ModelCaseStatus.DISMISSED: set(),
        ModelCaseStatus.ESCALATED: {ModelCaseStatus.RESOLVED, ModelCaseStatus.DISMISSED},
    }
    return new_status in valid_transitions.get(current_status, set())


def _is_terminal_status(status: ModelCaseStatus) -> bool:
    return status in {ModelCaseStatus.RESOLVED, ModelCaseStatus.DISMISSED}


def _validate_decision_for_status(case_status: ModelCaseStatus, decision: Optional[ModelCaseDecision]) -> None:
    """Validate that decision is consistent with status."""
    if case_status == ModelCaseStatus.RESOLVED:
        if decision is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Decision is required when resolving a case. Must be one of: true_positive, false_positive, inconclusive"
            )
        if decision not in {ModelCaseDecision.TRUE_POSITIVE, ModelCaseDecision.FALSE_POSITIVE, ModelCaseDecision.INCONCLUSIVE}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Resolved case must have decision: true_positive, false_positive, or inconclusive"
            )

    if case_status == ModelCaseStatus.ESCALATED:
        if decision is not None and decision not in {ModelCaseDecision.ESCALATED}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Escalated case must have decision=escalated or no decision"
            )

    if case_status == ModelCaseStatus.DISMISSED:
        if decision is not None and decision != ModelCaseDecision.FALSE_POSITIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Dismissed case must have decision=false_positive or no decision"
            )


@router.post("/investigations", response_model=InvestigationCaseResponse, status_code=status.HTTP_201_CREATED)
async def create_investigation_case(
    case_create: InvestigationCaseCreate,
    db: Session = Depends(get_db),
):
    """
    Create an investigation case from an existing risk event.

    The risk event must exist as either a Transaction or PaymentTransaction.
    """
    # Validate risk event exists
    if not _validate_risk_event_exists(db, case_create.risk_event_id, case_create.risk_event_type):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Risk event not found: {case_create.risk_event_type.value} with id {case_create.risk_event_id}"
        )

    # Check for existing case (unique constraint will also catch this)
    existing = db.query(InvestigationCase).filter(
        InvestigationCase.risk_event_id == case_create.risk_event_id,
        InvestigationCase.risk_event_type == case_create.risk_event_type.value
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Investigation case already exists for {case_create.risk_event_type.value} {case_create.risk_event_id}"
        )

    # Create case
    now = datetime.now(timezone.utc)
    case = InvestigationCase(
        risk_event_id=case_create.risk_event_id,
        risk_event_type=case_create.risk_event_type.value,
        status=ModelCaseStatus.PENDING,
        created_at=now,
        updated_at=now,
    )
    db.add(case)
    db.flush()

    # Create initial audit log
    _create_audit_log(
        db, case, None, "case_created",
        None,
        {"status": "pending", "risk_event_id": case.risk_event_id, "risk_event_type": case.risk_event_type}
    )

    db.commit()
    db.refresh(case)
    return case


@router.get("/investigations/{case_id}", response_model=InvestigationCaseResponse)
async def get_investigation_case(
    case_id: int,
    db: Session = Depends(get_db),
):
    """Get an investigation case by ID."""
    case = db.query(InvestigationCase).filter(InvestigationCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Investigation case not found")
    return case


@router.patch("/investigations/{case_id}", response_model=InvestigationCaseResponse)
async def update_investigation_case(
    case_id: int,
    case_update: InvestigationCaseUpdate,
    db: Session = Depends(get_db),
):
    """
    Update an investigation case.

    Supports partial updates of status, notes, and decision.
    Validates state transitions and records audit log entries.
    """
    case = db.query(InvestigationCase).filter(InvestigationCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Investigation case not found")

    update_data = case_update.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    # Capture old state for audit
    old_state = {
        "status": case.status.value,
        "notes": case.notes,
        "decision": case.decision.value if case.decision else None,
    }

    # Validate status transition if provided
    if "status" in update_data:
        new_status = ModelCaseStatus(update_data["status"])
        if not _validate_transition(case.status, new_status):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status transition: {case.status.value} -> {new_status.value}"
            )
        case.status = new_status

        # Set resolved_at for terminal states
        if _is_terminal_status(new_status) and case.resolved_at is None:
            case.resolved_at = datetime.now(timezone.utc)

    # Apply notes update
    if "notes" in update_data:
        case.notes = update_data["notes"]

    # Validate and apply decision
    if "decision" in update_data:
        if update_data["decision"] is not None:
            case.decision = ModelCaseDecision(update_data["decision"])
        else:
            case.decision = None

    # Validate decision consistency with status (after both may have been updated)
    target_status = case.status
    if "status" in update_data:
        target_status = ModelCaseStatus(update_data["status"])
    _validate_decision_for_status(target_status, case.decision)

    # Update timestamp
    case.updated_at = datetime.now(timezone.utc)

    # Create audit log
    new_state = {
        "status": case.status.value,
        "notes": case.notes,
        "decision": case.decision.value if case.decision else None,
    }
    _create_audit_log(db, case, None, "case_updated", old_state, new_state)

    db.commit()
    db.refresh(case)
    return case


@router.get("/investigations/{case_id}/audit-log", response_model=list[AuditLogResponse])
async def get_case_audit_log(
    case_id: int,
    db: Session = Depends(get_db),
):
    """Get audit log entries for an investigation case in chronological order."""
    case = db.query(InvestigationCase).filter(InvestigationCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Investigation case not found")

    audit_logs = db.query(AuditLog).filter(
        AuditLog.case_id == case_id
    ).order_by(AuditLog.timestamp.asc()).all()

    return audit_logs
