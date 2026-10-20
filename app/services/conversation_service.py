from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models.conversation_message import ConversationMessage

HISTORY_LIMIT = 10        # last 10 messages (5 back-and-forths)
HISTORY_MINUTES = 30      # ignore anything older than this


def load_history(db: Session, phone_number: str) -> list[dict]:
    stmt = (
        select(ConversationMessage)
        .where(
            ConversationMessage.phone_number == phone_number,
            ConversationMessage.created_at
            >= func.date_sub(func.now(), text(f"INTERVAL {HISTORY_MINUTES} MINUTE")),
        )
        .order_by(ConversationMessage.id.desc())
        .limit(HISTORY_LIMIT)
    )
    rows = list(db.scalars(stmt).all())
    rows.reverse()   # oldest first, the order the LLM expects
    return [{"role": r.role, "content": r.content} for r in rows]


def save_turn(db: Session, phone_number: str, user_text: str, reply: str) -> None:
    db.add(ConversationMessage(phone_number=phone_number, role="user", content=user_text))
    db.add(ConversationMessage(phone_number=phone_number, role="assistant", content=reply))
    db.commit()