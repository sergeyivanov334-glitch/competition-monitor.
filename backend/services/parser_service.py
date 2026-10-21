"""Совместимый вход к сбору страниц. Реализация — Selenium в parsingservice.py."""

from backend.services.parsingservice import PageSnapshot, parsing_service


class ParserService:
    def normalize_url(self, url: str) -> str:
        return parsing_service.normalize_url(url)

    async def capture(self, url: str):
        return await parsing_service.capture(url)


parser_service = ParserService()
