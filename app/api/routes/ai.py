from fastapi import APIRouter, File, Form, HTTPException, UploadFile


from app.ai.agent import handle_message
from app.api.deps import DbSession
from app.schemas.ai import AIMessageRequest, AIMessageResponse
from app.ai.transcription import (
    AudioRejected,
    TranscriptionError,
    TranscriptionTimeout,
    transcribe,
)
from sqlalchemy import select
from app.services.entry_point import process_text

from app.ai.agent import handle_message
from app.models.user import User
from app.ai.audio import AudioUnusable, to_wav16k
from app.core.config import settings

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/message", response_model=AIMessageResponse)
def message(payload: AIMessageRequest, db: DbSession):
    reply = process_text(db, payload.phone_number, payload.text, payload.message_id)
    return {"reply": reply}


@router.post("/voice")
def voice(
    db: DbSession,
    phone_number: str = Form(...),
    audio: UploadFile = File(...),
    transcribe_only: bool = Form(False),
):
    # 1. Find the trader
    user = db.scalar(select(User).where(User.phone_number == phone_number))
    language = user.language if user and user.language else settings.DEFAULT_STT_LANGUAGE

    if user is None:
        raise HTTPException(404, "User not found")

    try:
        raw = audio.file.read()
        wav_bytes, _ = to_wav16k(raw)
    except AudioUnusable as exc:
        print(
            f"audio rejected: {exc} | filename={audio.filename} "
            f"type={audio.content_type} bytes={len(raw)}",
            flush=True,
        )
        raise HTTPException(400, f"Audio problem: {exc}")

    try:
        text = transcribe(wav_bytes, "voice.wav", language)

    except AudioRejected:
        raise HTTPException(
            400, "Voice note too long or unreadable. Please send a shorter one."
        )
    except TranscriptionTimeout:
        raise HTTPException(504, "Transcription timed out. Please try again.")
    except TranscriptionError:
        raise HTTPException(422, "Couldn't make out any speech.")

    # The web UI reviews the transcript before any bookkeeping tools can run.
    if transcribe_only:
        return {"language": language, "transcript": text}

    # Other callers retain the existing direct-processing flow.
    reply = process_text(db, phone_number, text)
    return {"language": user.language, "transcript": text, "reply": reply}
