from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from datetime import datetime
from decimal import Decimal


from app.models.ledger_entry import LedgerEntry
from app.models.product import Product
from app.models.user import User
from app.schemas.ledger_entry import LedgerEntryCreate, Action


class UserNotFound(Exception):
    pass


class DuplicateMessage(Exception):
    pass


def normalize(name: str) -> str:
    return " ".join(name.lower().split())


def get_or_create_product(
    db: Session, user_id: int, name: str, unit: str | None
) -> Product:
    normalized = normalize(name)

    product = db.scalar(
        select(Product).where(
            Product.user_id == user_id,
            Product.normalized_name == normalized,
        )
    )
    if product is None:
        product = Product(
            user_id=user_id,
            name=name.strip(),
            normalized_name=normalized,
            default_unit=unit,
        )
        db.add(product)
        db.flush()  # populates product.id without committing
    return product


def create_entry(db: Session, payload: LedgerEntryCreate) -> LedgerEntry:
    # 1. Find the user from their WhatsApp number
    user = db.scalar(select(User).where(User.phone_number == payload.phone_number))
    if user is None:
        raise UserNotFound()

    # 2. Ignore WhatsApp webhook retries (same message delivered twice)
    if payload.whatsapp_message_id:
        already = db.scalar(
            select(LedgerEntry.id).where(
                LedgerEntry.whatsapp_message_id == payload.whatsapp_message_id,
                LedgerEntry.line_index == payload.line_index,
            )
        )
        if already:
            raise DuplicateMessage()

    # 3. Get or create the product for this user
    product = get_or_create_product(db, user.id, payload.product_name, payload.unit)

    # 4. Fill in missing numbers where we can
    unit_price = payload.unit_price
    if unit_price is None and payload.quantity:
        unit_price = payload.total_amount / payload.quantity

    # 5. Create the ledger entry
    entry = LedgerEntry(
        user_id=user.id,
        product_id=product.id,
        action=payload.action,
        total_amount=payload.total_amount,
        quantity=payload.quantity,
        unit=payload.unit,
        unit_price=unit_price,
        raw_text=payload.raw_text,
        whatsapp_message_id=payload.whatsapp_message_id,
        line_index=payload.line_index,
        **({"occurred_at": payload.occurred_at} if payload.occurred_at else {}),
    )
   
    db.add(entry)
    db.flush()     
    return entry


def create_entries(db: Session, payloads: list[LedgerEntryCreate]) -> list[LedgerEntry]:
    entries = []
    try:
        for payload in payloads:
            entries.append(create_entry(db, payload))
        db.commit()                 
    except Exception:
        db.rollback()               
        raise

    for entry in entries:
        db.refresh(entry)            
    return entries


def _base_filters(stmt, phone_number, action, date_from, date_to):
    stmt = stmt.join(User, LedgerEntry.user_id == User.id).where(
        User.phone_number == phone_number
    )
    if action:
        stmt = stmt.where(LedgerEntry.action == action)
    if date_from:
        stmt = stmt.where(LedgerEntry.occurred_at >= date_from)
    if date_to:
        stmt = stmt.where(LedgerEntry.occurred_at <= date_to)
    return stmt


def list_entries(
    db: Session,
    phone_number: str,
    action: Action | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[LedgerEntry]:
    stmt = _base_filters(select(LedgerEntry), phone_number, action, date_from, date_to)
    stmt = (
        stmt.options(
            joinedload(LedgerEntry.product)
        )  # avoids N+1 when returning product
        .order_by(LedgerEntry.occurred_at.desc(), LedgerEntry.id.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(db.scalars(stmt).all())


def get_entry(db: Session, entry_id: int, phone_number: str) -> LedgerEntry:
    entry = db.scalar(
        select(LedgerEntry)
        .join(User, LedgerEntry.user_id == User.id)
        .where(LedgerEntry.id == entry_id, User.phone_number == phone_number)
        .options(joinedload(LedgerEntry.product))
    )
    if entry is None:
        raise EntryNotFound()
    return entry


def delete_entry(db: Session, entry_id: int, phone_number: str) -> None:
    entry = get_entry(db, entry_id, phone_number)
    db.delete(entry)
    db.commit()


def get_summary(
    db: Session,
    phone_number: str,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> dict:
    stmt = _base_filters(
        select(
            LedgerEntry.action,
            func.coalesce(func.sum(LedgerEntry.total_amount), 0),
            func.count(),
        ),
        phone_number,
        None,
        date_from,
        date_to,
    ).group_by(LedgerEntry.action)

    totals = {Action.SALE: Decimal(0), Action.PURCHASE: Decimal(0)}
    counts = {Action.SALE: 0, Action.PURCHASE: 0}
    for action, total, count in db.execute(stmt).all():
        totals[action] = Decimal(total)
        counts[action] = count

    return {
        "total_sales": totals[Action.SALE],
        "total_purchases": totals[Action.PURCHASE],
        "net": totals[Action.SALE] - totals[Action.PURCHASE],
        "sales_count": counts[Action.SALE],
        "purchases_count": counts[Action.PURCHASE],
    }
