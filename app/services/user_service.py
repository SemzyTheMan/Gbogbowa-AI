import json
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.client import client
from app.core.config import settings
from app.models.user import User



LANGUAGES = {
    "en":  {"label": "English", "aliases": ["1", "english"]},
    "pcm": {"label": "Pidgin",  "aliases": ["2", "pidgin", "pidgin english", "naija"]},
    "ig":  {"label": "Igbo",    "aliases": ["3", "igbo", "ibo"]},
    "yo":  {"label": "Yoruba",  "aliases": ["4", "yoruba"]},
    "ha":  {"label": "Hausa",   "aliases": ["5", "hausa"]},
}
# check Pidgin before English so "pidgin english" doesn't match "english"
MATCH_ORDER = ["pcm", "ig", "yo", "ha", "en"]

LANGUAGE_MENU = (
    "Which language should I listen for in your voice notes?\n"
    "1. English\n2. Pidgin\n3. Igbo\n4. Yoruba\n5. Hausa\n"
    "Reply with the number or the name."
)


def match_language(text: str) -> str | None:
    t = re.sub(r"[^\w\s]", " ", text.lower())
    t = re.sub(r"\s+", " ", t).strip()
    for code in MATCH_ORDER:
        for alias in LANGUAGES[code]["aliases"]:
            if alias.isdigit():
                if t == alias:
                    return code
            elif re.search(rf"\b{re.escape(alias)}\b", t):
                return code
    return None


def extract_intro(text: str) -> dict:
    """Pull the trader's name and market location out of a self-introduction."""
    resp = client.chat.completions.create(
        model=settings.LLM_MODEL,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": (
                "Extract the speaker's name and where they sell from a short self-introduction. "
                "Keep the name as spoken, including titles like Mrs or Mr. Do not invent anything. "
                'Reply as JSON: {"name": string or null, "location": string or null}'
            )},
            {"role": "user", "content": text},
        ],
    )
    try:
        data = json.loads(resp.choices[0].message.content)
    except (ValueError, TypeError):
        data = {}
    return {
        "name": (data.get("name") or "").strip() or None,
        "location": (data.get("location") or "").strip() or None,
    }


def start_onboarding(db: Session, phone: str, text: str) -> str:
    intro = extract_intro(text)
    user = User(
        phone_number=phone,
        user_name=intro["name"] or "Trader",
        location=intro["location"],
        language=None,
    )
    db.add(user)
    db.commit()

    greeting = f"Welcome, {intro['name']}!" if intro["name"] else "Welcome!"
    where = f" Selling at {intro['location']}, nice." if intro["location"] else ""
    return f"{greeting}{where}\n\n{LANGUAGE_MENU}"


def finish_onboarding(db: Session, user: User, text: str) -> str:
    code = match_language(text)
    if code is None:
        return f"Sorry, I didn't catch that.\n\n{LANGUAGE_MENU}"
    user.language = code
    db.commit()
    label = LANGUAGES[code]["label"]
    return (f"Done, I'll listen for {label}. "
            "Now tell me what you bought or sold, for example: "
            "\"I sold 2 bags of rice for 18,000\".")


def request_language_change(db: Session, user: User) -> str:
    user.language = None
    db.commit()
    return LANGUAGE_MENU

