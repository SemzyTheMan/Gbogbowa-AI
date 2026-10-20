
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import DbSession
from app.models.ledger_entry import Action
from app.schemas.ledger_entry import LedgerEntryCreate, LedgerEntryRead, LedgerSummary
from app.services import ledger_service

router = APIRouter(prefix="/ledger", tags=["ledger"])


@router.post("/", response_model=LedgerEntryRead, status_code=status.HTTP_201_CREATED)
def create_entry(payload: LedgerEntryCreate, db: DbSession):
    try:
        return ledger_service.create_entries(db, [payload])[0]
    except ledger_service.UserNotFound:
        raise HTTPException(status_code=404, detail="User not found")
    except ledger_service.DuplicateMessage:
        raise HTTPException(status_code=409, detail="Message already processed")


@router.get("/", response_model=list[LedgerEntryRead])
def list_entries(
    db: DbSession,
    phone_number: str,
    action: Action | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    return ledger_service.list_entries(
        db, phone_number, action, date_from, date_to, skip, limit
    )


@router.get("/summary", response_model=LedgerSummary)
def get_summary(
    db: DbSession,
    phone_number: str,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
):
    return ledger_service.get_summary(db, phone_number, date_from, date_to)


@router.get("/{entry_id}", response_model=LedgerEntryRead)
def get_entry(entry_id: int, phone_number: str, db: DbSession):
    try:
        return ledger_service.get_entry(db, entry_id, phone_number)
    except ledger_service.EntryNotFound:
        raise HTTPException(status_code=404, detail="Entry not found")


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entry(entry_id: int, phone_number: str, db: DbSession):
    try:
        ledger_service.delete_entry(db, entry_id, phone_number)
    except ledger_service.EntryNotFound:
        raise HTTPException(status_code=404, detail="Entry not found")