from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.ledger_entry import Action
from app.schemas.ledger_entry import LedgerEntryCreate
from app.services import ledger_service


def _parse_date(value: str | None, end_of_day: bool = False) -> datetime | None:
    if not value:
        return None
    d = datetime.fromisoformat(value)
    return d.replace(hour=23, minute=59, second=59) if end_of_day else d


def record_entries(db: Session, phone_number: str, message_id: str | None, args: dict) -> dict:
    payloads = [
        LedgerEntryCreate(
            phone_number=phone_number,
            whatsapp_message_id=message_id,
            line_index=i,
            action=Action(item["action"]),
            product_name=item["product_name"],
            total_amount=Decimal(str(item["total_amount"])),
            quantity=item.get("quantity"),
            unit=item.get("unit"),
            occurred_at=_parse_date(item.get("occurred_on")),
            raw_text=args.get("raw_text"),
        )
        for i, item in enumerate(args["entries"])
    ]
    entries = ledger_service.create_entries(db, payloads)
    return {"saved": len(entries), "total": str(sum(e.total_amount for e in entries))}


def get_summary(db: Session, phone_number: str, message_id: str | None, args: dict) -> dict:
    summary = ledger_service.get_summary(
        db,
        phone_number,
        _parse_date(args.get("date_from")),
        _parse_date(args.get("date_to"), end_of_day=True),
    )
    return {k: str(v) for k, v in summary.items()}


HANDLERS = {
    "record_entries": record_entries,
    "get_summary": get_summary,
}


def run_tool(db: Session, phone_number: str, message_id: str | None, name: str, args: dict) -> dict:
    handler = HANDLERS.get(name)
    if handler is None:
        return {"error": f"Unknown tool {name}"}
    try:
        return handler(db, phone_number, message_id, args)
    except ledger_service.UserNotFound:
        return {"error": "This phone number is not registered."}
    except ledger_service.DuplicateMessage:
        return {"error": "This message was already recorded."}
    except Exception as e:
        db.rollback()
        return {"error": f"Could not complete: {e}"}
