import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from app.api.deps import get_db
from app.main import app


class VoicePreviewTests(unittest.TestCase):
    def setUp(self):
        self.db = Mock()
        self.db.scalar.return_value = SimpleNamespace(language="yo")
        app.dependency_overrides[get_db] = lambda: self.db
        self.client = TestClient(app)
        self.addCleanup(app.dependency_overrides.clear)

    @patch("app.api.routes.ai.process_text")
    @patch("app.api.routes.ai.transcribe", return_value="Mo ta epo pupa fún 1515,000")
    @patch("app.api.routes.ai.to_wav16k", return_value=(b"wav", 1.0))
    def test_preview_returns_raw_transcript_without_recording(self, convert, transcribe, process):
        response = self.client.post(
            "/ai/voice",
            data={"phone_number": "+2348012345678", "transcribe_only": "true"},
            files={"audio": ("voice.webm", b"audio", "audio/webm")},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"language": "yo", "transcript": transcribe.return_value})
        transcribe.assert_called_once_with(b"wav", "voice.wav", "yo")
        process.assert_not_called()
        self.db.commit.assert_not_called()

    @patch("app.api.routes.ai.process_text", return_value="Recorded")
    @patch("app.api.routes.ai.transcribe", return_value="Mo ta epo pupa fun 15000")
    @patch("app.api.routes.ai.to_wav16k", return_value=(b"wav", 1.0))
    def test_existing_voice_callers_still_process_directly(self, convert, transcribe, process):
        response = self.client.post(
            "/ai/voice", data={"phone_number": "+2348012345678"},
            files={"audio": ("voice.webm", b"audio", "audio/webm")},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["reply"], "Recorded")
        process.assert_called_once_with(self.db, "+2348012345678", transcribe.return_value)


if __name__ == "__main__":
    unittest.main()
