from datetime import datetime

from sqlalchemy import ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("user_id", "normalized_name", name="uq_user_product"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    name: Mapped[str] = mapped_column(String(255))              # as the trader said it: "Bag of Rice"
    normalized_name: Mapped[str] = mapped_column(String(255))   # lowercase, trimmed: "bag of rice"
    default_unit: Mapped[str | None] = mapped_column(String(50))  # "bag", "basket", "derica", optional
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="products")
    entries: Mapped[list["LedgerEntry"]] = relationship(back_populates="product")