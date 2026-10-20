import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.db.base import Base
from app.main import app
from app.models.ledger_entry import LedgerEntry
from app.models.user import User


def response(content=None, entries=None):
    calls = [] if entries is None else [SimpleNamespace(
        id="call_record", function=SimpleNamespace(
            name="record_entries", arguments=json.dumps({"entries": entries})
        )
    )]
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content, tool_calls=calls))])


class TextRecordingTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
        Base.metadata.create_all(engine)
        self.db = Session(engine)
        self.addCleanup(engine.dispose)
        self.addCleanup(self.db.close)
        self.phone = "+2348012345678"
        self.db.add(User(phone_number=self.phone, user_name="Test trader", language="yo"))
        self.db.commit()
        app.dependency_overrides[get_db] = lambda: self.db
        self.addCleanup(app.dependency_overrides.clear)
        self.client = TestClient(app)
        self.history = patch("app.ai.agent.conversation_service.load_history", return_value=[
            {"role": "user", "content": "Mo ta epo pupa igo 2 fun 15000"},
            {"role": "assistant", "content": "Recorded: Sold palm oil for 15000."},
        ])
        self.history.start()
        self.addCleanup(self.history.stop)
        self.entry = {"action": "sale", "product_name": "epo pupa", "total_amount": 15000, "quantity": 2, "unit": "igo"}

    def send(self, message_id="web-message-1"):
        return self.client.post("/ai/message", json={
            "phone_number": self.phone, "text": "Mo ta epo pupa igo 2 fun 15000", "message_id": message_id,
        })

    @patch("app.ai.agent.client.chat.completions.create")
    def test_false_confirmation_is_retried_and_committed(self, complete):
        complete.side_effect = [response("Recorded: Sold palm oil for 15000."), response(entries=[self.entry])]
        result = self.send()
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["reply"], "Recorded: 1 entry, ₦15,000.00 total.")
        self.db.expire_all()
        rows = self.db.scalars(select(LedgerEntry)).all()
        self.assertEqual(len(rows), 1)
        self.assertEqual(int(rows[0].total_amount), 15000)
        self.assertEqual(rows[0].whatsapp_message_id, "web-message-1")
        self.assertEqual(rows[0].raw_text, "Mo ta epo pupa igo 2 fun 15000")
        self.assertEqual(complete.call_count, 2)

    @patch("app.ai.agent.client.chat.completions.create")
    def test_persistent_false_confirmation_is_not_reported_as_saved(self, complete):
        complete.return_value = response("Recorded: Sold palm oil for 15000.")
        result = self.send()
        self.assertIn("No new entry was saved", result.json()["reply"])
        self.assertEqual(self.db.scalars(select(LedgerEntry)).all(), [])

    @patch("app.ai.agent.client.chat.completions.create")
    def test_write_failure_cannot_be_reported_as_recorded(self, complete):
        complete.return_value = response(entries=[{**self.entry, "total_amount": -1}])
        result = self.send()
        self.assertIn("could not be saved", result.json()["reply"])
        self.assertEqual(self.db.scalars(select(LedgerEntry)).all(), [])
        self.assertEqual(complete.call_count, 1)

    @patch("app.ai.agent.client.chat.completions.create")
    def test_duplicate_message_does_not_create_second_entry(self, complete):
        complete.return_value = response(entries=[self.entry])
        self.send()
        result = self.send()
        self.assertIn("already recorded", result.json()["reply"])
        self.assertEqual(len(self.db.scalars(select(LedgerEntry)).all()), 1)

    @patch("app.ai.agent.client.chat.completions.create")
    def test_ambiguous_instruction_can_still_ask_without_writing(self, complete):
        complete.return_value = response("Is that price per bottle or the total?")
        result = self.send()
        self.assertEqual(result.json()["reply"], "Is that price per bottle or the total?")
        self.assertEqual(self.db.scalars(select(LedgerEntry)).all(), [])


if __name__ == "__main__":
    unittest.main()
