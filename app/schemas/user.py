from datetime import datetime
from pydantic import BaseModel, ConfigDict


class UserCreate(BaseModel):
    phone_number: str
    user_name: str
    language:str
    location:str


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    phone_number: str
    user_name: str
    created_at: datetime