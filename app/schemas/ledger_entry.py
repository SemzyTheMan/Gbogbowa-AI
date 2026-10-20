from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.ledger_entry import Action


class LedgerEntryCreate(BaseModel):
    phone_number: str                       # identifies the trader
    product_name: str = Field(min_length=1, max_length=255)
    action: Action
    total_amount: Decimal = Field(gt=0)
    line_index: int = 0

    quantity: Decimal | None = Field(default=None, gt=0)
    unit: str | None = Field(default=None, max_length=50)
    unit_price: Decimal | None = Field(default=None, ge=0)

    raw_text: str | None = None
    whatsapp_message_id: str | None = None
    occurred_at: datetime | None = None    


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str

class LedgerSummary(BaseModel):
    total_sales: Decimal
    total_purchases: Decimal
    net: Decimal            # sales minus purchases (cash view, not true profit)
    sales_count: int
    purchases_count: int

class LedgerEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    action: Action
    total_amount: Decimal
    quantity: Decimal | None
    unit: str | None
    unit_price: Decimal | None
    occurred_at: datetime
    created_at: datetime

    product: ProductRead                    # nested, read via the relationship