from datetime import datetime
from sqlalchemy import String, func
from sqlalchemy.orm import Mapped, mapped_column,relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    phone_number: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    user_name: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable = True)   

    products: Mapped[list["Product"]] = relationship(back_populates="user")
    entries: Mapped[list["LedgerEntry"]] = relationship(back_populates="user")