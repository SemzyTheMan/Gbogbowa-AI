from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.api.routes import users, ledger_entries, ai, whatsapp
from app.core.config import settings

app = FastAPI(title=settings.PROJECT_NAME)
STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(STATIC_DIR / "index.html")

app.include_router(users.router)
app.include_router(ledger_entries.router)
app.include_router(ai.router)
app.include_router(whatsapp.router)


@app.get("/health")
def health():
    return {"status": "ok"}
