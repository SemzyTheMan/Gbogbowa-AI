import logging

from app.ai.audio import AudioUnusable
from app.services.entry_point import process_text
from app.ai.transcription import AudioRejected, TranscriptionError, TranscriptionTimeout
from app.ai.voice import voice_to_text
from app.db.session import SessionLocal
from app.whatsapp.twilio_client import download_media, send_whatsapp

log = logging.getLogger(__name__)

ECHO_TRANSCRIPT = True  


def process_incoming(phone: str, body: str, media_url: str | None,
                     media_type: str | None, message_sid: str) -> None:
    # A background task must open its OWN session; the request's session is gone by now
    with SessionLocal() as db:
        try:
            if media_url and (media_type or "").startswith("audio"):
                try:
                    text = voice_to_text(db, phone, download_media(media_url))
                except AudioUnusable:
                    reply = "I couldn't hear that clearly. Please send a clear voice note under 2 minutes."
                except AudioRejected:
                    reply = "That voice note is too long or unreadable. Please send a shorter one."
                except TranscriptionTimeout:
                    reply = "That took too long. Please try again."
                except TranscriptionError:
                    reply = "I couldn't make out any speech. Please try again."
                else:
                    reply = process_text(db, phone, text, message_sid)
                    if ECHO_TRANSCRIPT:
                        reply = f'I heard: "{text}"\n\n{reply}'
            elif body.strip():
                reply = process_text(db, phone, body.strip(), message_sid)
            else:
                reply = "Please send a text message or a voice note."
        except Exception:
            log.exception("Failed to process message %s", message_sid)
            db.rollback()
            reply = "Sorry, something went wrong on my side. Please try again."

    try:
        send_whatsapp(phone, reply)
    except Exception:
        log.exception("Failed to send reply for %s", message_sid)