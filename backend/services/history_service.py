"""Хранение последних запросов в history.json."""

import json
import uuid
from datetime import datetime
from typing import List

from backend.config import settings
from backend.models.schemas import HistoryItem


class HistoryService:
    def __init__(self) -> None:
        self.history_file = settings.history_path
        self.max_items = settings.max_history_items
        self._ensure_file_exists()

    def _ensure_file_exists(self) -> None:
        if not self.history_file.exists():
            self.history_file.write_text("[]", encoding="utf-8")

    def _load_history(self) -> List[dict]:
        try:
            content = self.history_file.read_text(encoding="utf-8")
            data = json.loads(content)
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, FileNotFoundError, OSError):
            return []

    def _save_history(self, history: List[dict]) -> None:
        self.history_file.write_text(
            json.dumps(history, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def add_entry(
        self,
        request_type: str,
        request_summary: str,
        response_summary: str,
    ) -> HistoryItem:
        history = self._load_history()
        item = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "request_type": request_type,
            "request_summary": request_summary[:200],
            "response_summary": response_summary[:500],
        }
        history.insert(0, item)
        self._save_history(history[: self.max_items])
        return HistoryItem(**item)

    def get_history(self) -> List[HistoryItem]:
        return [HistoryItem(**item) for item in self._load_history()]

    def clear_history(self) -> None:
        self._save_history([])


history_service = HistoryService()
