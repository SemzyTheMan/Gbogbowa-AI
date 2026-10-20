from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Response
from twilio.request_validator import RequestValidator

from app.core.config import settings
from app.whatsapp.handler import process_incoming

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])
validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)

import logging
log = logging.getLogger(__name__)




@router.post("/webhook")
async def webhook(request: Request, background: BackgroundTasks):
    form = await request.form()
    params = {k: str(v) for k, v in form.items()}
    log.warning("Inbound To=%r | .env From=%r", params.get("To"), settings.TWILIO_WHATSAPP_NUMBER)
    # 1. Verify the request really came from Twilio
    url = f"{settings.PUBLIC_BASE_URL}{request.url.path}"
    if not validator.validate(url, params, request.headers.get("X-Twilio-Signature", "")):
        raise HTTPException(403, "Invalid signature")

    # 2. 'whatsapp:+2348012345678' -> '2348012345678' (matches users.phone_number)
    phone = params["From"].removeprefix("whatsapp:").lstrip("+")

    # 3. Hand off, then answer Twilio immediately
    background.add_task(
        process_incoming,
        phone,
        params.get("Body", ""),
        params.get("MediaUrl0"),
        params.get("MediaContentType0"),
        params["MessageSid"],
    )
    return Response(content="<Response/>", media_type="application/xml")