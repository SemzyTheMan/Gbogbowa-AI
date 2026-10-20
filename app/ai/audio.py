import io
import wave

import av

TARGET_RATE = 16000
MIN_SECONDS = 0.5
MAX_SECONDS = 120   # Intron's sync limit


class AudioUnusable(ValueError):
    pass


def to_wav16k(blob: bytes) -> tuple[bytes, float]:
    """Decode any common audio format to 16 kHz mono WAV. Returns (wav_bytes, seconds)."""
    try:
        chunks: list[bytes] = []
        with av.open(io.BytesIO(blob)) as container:
            stream = container.streams.audio[0]
            resampler = av.AudioResampler(format="s16", layout="mono", rate=TARGET_RATE)
            for frame in container.decode(stream):
                for out in resampler.resample(frame):
                    chunks.append(out.to_ndarray().tobytes())   # NOT the raw plane buffer
            for out in resampler.resample(None):                # flush
                chunks.append(out.to_ndarray().tobytes())
    except Exception as exc:
        raise AudioUnusable(f"undecodable audio: {exc}") from exc

    pcm = b"".join(chunks)
    seconds = len(pcm) / 2 / TARGET_RATE
    if seconds < MIN_SECONDS:
        raise AudioUnusable("clip too short")
    if seconds > MAX_SECONDS:
        raise AudioUnusable("clip too long")

    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(TARGET_RATE)
        w.writeframes(pcm)
    return buf.getvalue(), seconds