from pydantic import BaseModel


class AIMessageRequest(BaseModel):
    phone_number: str
    text: str
    message_id: str | None = None


class AIMessageResponse(BaseModel):
    reply: str