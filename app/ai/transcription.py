import httpx

from app.core.config import settings

INTRON_URL = "https://infer.voice.intron.io/file/v1/upload/sync"


class TranscriptionError(Exception):
    pass


class AudioRejected(TranscriptionError):
    """400: usually audio longer than 120 seconds, or an unsupported file."""


class TranscriptionTimeout(TranscriptionError):
    pass


def transcribe(audio_bytes: bytes, filename: str = "voice.ogg", language: str = "en") -> str:
    try:
        resp = httpx.post(
            INTRON_URL,
            headers={"Authorization": f"Bearer {settings.INTRON_API_KEY}"},
            data={
                "audio_file_name": filename,
                "use_language_asr_input": language,
                "use_category": "file_category_general",
                "use_disable_llm_corrections": "TRUE",  
            },
            files={"audio_file_blob": (filename, audio_bytes, "audio/wav")},
            timeout=130,  
        )
    except httpx.TimeoutException:
        raise TranscriptionTimeout()

    if resp.status_code == 400:
        raise AudioRejected(resp.text)
    if resp.status_code == 503:
        raise TranscriptionTimeout()
    resp.raise_for_status()

    transcript = resp.json()["data"]["audio_transcript"]
    if not transcript.strip():
        raise TranscriptionError("Empty transcript")
    return transcript