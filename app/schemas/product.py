from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    default_unit: str | None = Field(default=None, max_length=50)


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    default_unit: str | None = Field(default=None, max_length=50)


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    default_unit: str | None
    created_at: datetime