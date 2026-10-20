from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import Enum as SAEnum, ForeignKey, Numeric, String, Text, func,UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Action(str, Enum):
    PURCHASE = "purchase"
    SALE = "sale"


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    __table_args__ = (
        UniqueConstraint("whatsapp_message_id", "line_index", name="uq_message_line"),
    )


    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)

    action: Mapped[Action] = mapped_column(SAEnum(Action))

  
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))

  
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))   # allows 2.5 bags
    unit: Mapped[str | None] = mapped_column(String(50))               # "bag", "basket", "kg"
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))

   
    raw_text: Mapped[str | None] = mapped_column(Text)                 # the transcript
    whatsapp_message_id: Mapped[str | None] = mapped_column(String(100))  
    line_index: Mapped[int] = mapped_column(default=0)

    occurred_at: Mapped[datetime] = mapped_column(server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="entries")
    product: Mapped["Product"] = relationship(back_populates="entries")