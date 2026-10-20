import re

from app.ai.agent import handle_message
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.user import User
from app.services.user_service import (
    finish_onboarding,
    request_language_change,
    start_onboarding,
)


def process_text(
    db: Session, phone: str, text: str, message_id: str | None = None
) -> str:
    user = db.scalar(select(User).where(User.phone_number == phone))

    if user is None:
        return start_onboarding(db, phone, text)

    if user.language is None:
        return finish_onboarding(db, user, text)

    if re.search(r"\b(change|switch)\b.*\blanguage\b", text.lower()):
        return request_language_change(db, user)

    return handle_message(db, phone, text, message_id)
