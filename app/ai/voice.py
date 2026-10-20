from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.audio import to_wav16k         
from app.ai.transcription import transcribe 
from app.core.config import settings
from app.models.user import User


def voice_to_text(db: Session, phone: str, raw_audio: bytes) -> str:
    user = db.scalar(select(User).where(User.phone_number == phone))
    language = user.language if user and user.language else settings.DEFAULT_STT_LANGUAGE
    wav_bytes, _ = to_wav16k(raw_audio)
    return transcribe(wav_bytes, "voice.wav", language)