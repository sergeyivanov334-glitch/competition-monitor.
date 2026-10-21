"""Фоновые запросы к тем же сервисам, что и веб-приложение."""

import asyncio
import base64
import json
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from backend.config import settings
from backend.services.history_service import history_service
from backend.services.monitor_service import monitor_service
from backend.services.openai_service import get_openai_service
from backend.services.parser_service import parser_service

IMAGE_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


def clip(text: str, limit: int) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


class AnalyzeWorker(QThread):
    succeeded = pyqtSignal(str, object)
    failed = pyqtSignal(str)

    def __init__(self, kind: str, payload: str) -> None:
        super().__init__()
        self.kind = kind
        self.payload = payload

    def run(self) -> None:
        try:
            result = asyncio.run(self._run())
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        self.succeeded.emit(self.kind, result)

    async def _run(self):
        if self.kind == "text":
            return await self._text(self.payload)
        if self.kind == "image":
            return await self._image(self.payload)
        if self.kind == "parse":
            return await self._parse(self.payload)
        if self.kind == "monitor":
            data = json.loads(self.payload)
            return await monitor_service.run(urls=data.get("urls"), niche=data.get("niche"))
        if self.kind == "monitor_scheduled":
            return await monitor_service.run(scheduled=True)
        raise RuntimeError("Неизвестный запрос")

    async def _text(self, text: str):
        service = get_openai_service()
        analysis = await service.analyze_text(text)
        history_service.add_entry(
            request_type="text",
            request_summary=clip(text, 180),
            response_summary=analysis.summary or "Анализ текста выполнен",
        )
        return analysis

    async def _image(self, path: str):
        file_path = Path(path)
        mime = IMAGE_TYPES.get(file_path.suffix.lower())
        if not mime:
            raise RuntimeError("Нужен файл PNG, JPG, GIF или WEBP")
        content = file_path.read_bytes()
        if not content:
            raise RuntimeError("Файл пустой")
        if len(content) > settings.max_image_bytes:
            raise RuntimeError("Файл больше 10 МБ")

        service = get_openai_service()
        analysis = await service.analyze_image(
            image_base64=base64.b64encode(content).decode("ascii"),
            mime_type=mime,
        )
        history_service.add_entry(
            request_type="image",
            request_summary=f"Изображение: {file_path.name}",
            response_summary=analysis.description or "Анализ изображения выполнен",
        )
        return analysis

    async def _parse(self, url: str):
        snapshot, error = await parser_service.capture(url)
        if error or snapshot is None:
            raise RuntimeError(error or "Страница не открылась")

        service = get_openai_service()
        shot = base64.b64encode(snapshot.screenshot_png).decode("ascii")
        analysis = await service.analyze_page(
            image_base64=shot,
            url=snapshot.url,
            title=snapshot.title,
            text=snapshot.text,
            niche=settings.niche,
        )
        history_service.add_entry(
            request_type="parse",
            request_summary=f"URL: {snapshot.url}",
            response_summary=snapshot.title or analysis.summary or "Страница разобрана",
        )
        return {
            "url": snapshot.url,
            "title": snapshot.title,
            "screenshot": snapshot.screenshot_png,
            "analysis": analysis,
        }
