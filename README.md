# Gbogbowa inventory

A single-page business assistant served by the existing FastAPI application.

## Run

With the project's Python environment activated and `.env` configured:

```powershell
python -m uvicorn app.main:app --reload
```

Open http://localhost:8000. The UI is served at `/`; API documentation remains at `/docs`.

## Use

Enter the same phone number used for your trader account, including its country code. New traders can type a greeting and follow the existing assistant onboarding flow before using voice.

Tap the microphone to start recording, then tap again to stop. Listen back before selecting **Review transcript**. Check and edit the recognized words and prices in the text box, then tap Send to process the instruction. Transcribing alone does not save ledger entries. Recordings stop automatically just before the server's two-minute limit. You can also type instructions or select a suggested prompt to edit before sending.

- Text instructions use `POST /ai/message` with `phone_number`, `text`, and a generated `message_id`.
- The web UI uses `POST /ai/voice` with multipart fields `phone_number`, `audio`, and `transcribe_only=true`, then sends the reviewed text to `/ai/message`. Existing API callers that omit `transcribe_only` retain direct processing.
- Responses appear in the conversation panel. Conversations stay in page memory; only the phone number is remembered in this browser.

Microphone access requires HTTPS on a deployed site, or localhost during development. Google Fonts are optional; local font fallbacks work without internet access.

The existing API identifies traders by phone number without authentication. Add authentication and account ownership checks before exposing real business records publicly.
