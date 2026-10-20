import json
import re
from decimal import Decimal

from sqlalchemy.orm import Session

from app.ai.client import client
from app.ai.handlers import run_tool
from app.ai.prompts import build_system_prompt
from app.ai.tools import TOOLS
from app.core.config import settings
from app.services import conversation_service

MAX_STEPS = 5


def _claims_recorded(reply: str) -> bool:
    return bool(re.search(r"\b(recorded|saved|logged|registered|added to (?:the |your )?(?:ledger|records|database))\b", reply, re.I))


def handle_message(db: Session, phone_number: str, text: str, message_id: str | None = None) -> str:
    history = conversation_service.load_history(db, phone_number)

    messages = [
        {"role": "system", "content": build_system_prompt(db, phone_number)},
        *history,                                  
        {"role": "user", "content": text},        
    ]

    reply = None
    checked_without_tools = False
    used_tools = False
    saved_count = 0
    saved_total = Decimal(0)
    for _ in range(MAX_STEPS):
        response = client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=messages,
            tools=TOOLS,
            temperature=0,
        )
        msg = response.choices[0].message

        if not msg.tool_calls:
            if not used_tools and not checked_without_tools:
                # History contains conversational replies, not evidence of a save
                # for this request. Give a skipped recording tool one retry.
                checked_without_tools = True
                messages.append({"role": "system", "content": (
                    "No tool has run for the current user message and no new ledger entry has been saved. "
                    "Previous assistant confirmations are history, not proof that this request was recorded. "
                    "If the current instruction gives a clear new purchase or sale, call record_entries now. "
                    "If it is ambiguous, ask a question instead. Never claim a save without a successful tool result."
                )})
                continue
            reply = msg.content or ""
            if not saved_count and _claims_recorded(reply):
                reply = "No new entry was saved. Please send the item, amount, and whether you bought or sold it."
            break

        used_tools = True
        messages.append(msg)
        for call in msg.tool_calls:
            args = json.loads(call.function.arguments)
            if call.function.name == "record_entries":
                args["raw_text"] = text
            result = run_tool(db, phone_number, message_id, call.function.name, args)
            if call.function.name == "record_entries":
                if result.get("error"):
                    # Do not let a later model reply turn a failed write into success.
                    reply = (
                        "This message was already recorded; no new entry was added."
                        if result["error"] == "This message was already recorded."
                        else "The entry could not be saved. Please check your records before retrying."
                    )
                    break
                saved_count += result.get("saved", 0)
                saved_total += Decimal(result.get("total", "0"))
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": json.dumps(result),
            })
        if saved_count:
            # create_entries commits before returning this result. Build the
            # confirmation from that result, not from generated assistant text.
            confirmation = f"Recorded: {saved_count} {'entry' if saved_count == 1 else 'entries'}, ₦{saved_total:,.2f} total."
            reply = f"{confirmation} Another entry could not be saved; check your records before retrying." if reply else confirmation
            break
        if reply is not None:
            break

    if reply is None:
        return "Sorry, I couldn't process that. Please try again."

    conversation_service.save_turn(db, phone_number, text, reply)
    return reply
