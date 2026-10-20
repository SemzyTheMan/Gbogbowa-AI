import httpx
from twilio.rest import Client

from app.core.config import settings

_client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)



import logging
from twilio.base.exceptions import TwilioRestException

log = logging.getLogger(__name__)


def send_whatsapp(phone: str, body: str) -> None:
    recipient = phone.strip().removeprefix("whatsapp:").lstrip("+")
    sender = settings.TWILIO_WHATSAPP_NUMBER.strip()

    try:
        message = _client.messages.create(
            from_=sender,
            to=f"whatsapp:+{recipient}",
            body=body[:1500],
        )
        log.info("WhatsApp message accepted: %s", message.sid)

    except TwilioRestException as exc:
        log.error(
            "WhatsApp send failed: status=%s code=%s message=%s",
            exc.status,
            exc.code,
            exc.msg,
        )
        raise

def download_media(url: str) -> bytes:
    resp = httpx.get(
        url,
        auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN),
        follow_redirects=True,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.content