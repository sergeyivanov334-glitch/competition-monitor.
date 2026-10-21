"""Анализ текста и изображений через OpenAI-совместимый API."""

import json
import re
from typing import Optional

from openai import AsyncOpenAI

from backend.config import settings
from backend.models.schemas import CompetitorAnalysis, ImageAnalysis
from backend.services.openaiservice import (
    IMAGE_PROMPT,
    PAGE_PROMPT,
    TEXT_PROMPT,
    competitor_from_json,
    image_from_json,
    prompt_for,
)


class OpenAIService:
    def __init__(self) -> None:
        provider = settings.llm_provider.strip().lower()
        if provider == "proxy":
            api_key = settings.proxy_api
            base_url = settings.proxy_base_url
            self.model = settings.proxy_model
            self.vision_model = settings.proxy_vision_model
            key_hint = "PROXY_API"
        else:
            api_key = settings.openai_api_key
            base_url = None
            self.model = settings.openai_model
            self.vision_model = settings.openai_vision_model
            key_hint = "OPENAI_API_KEY"

        if not api_key:
            raise RuntimeError(
                f"Не задан ключ {key_hint}. Скопируйте .env.example в .env и заполните его."
            )

        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    @staticmethod
    def _parse_json(content: str) -> dict:
        if not content:
            return {}
        fenced = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content)
        if fenced:
            content = fenced.group(1)
        obj = re.search(r"\{[\s\S]*\}", content)
        if obj:
            content = obj.group(0)
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}

    async def analyze_text(self, text: str, niche: str = "") -> CompetitorAnalysis:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": prompt_for(TEXT_PROMPT, niche or settings.niche)},
                {"role": "user", "content": f"Проанализируй текст конкурента:\n\n{text}"},
            ],
            temperature=0.4,
            max_tokens=1800,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or ""
        return competitor_from_json(self._parse_json(content), content)

    async def analyze_image(
        self,
        image_base64: str,
        mime_type: str,
        niche: str = "",
    ) -> ImageAnalysis:
        response = await self.client.chat.completions.create(
            model=self.vision_model,
            messages=[
                {"role": "system", "content": prompt_for(IMAGE_PROMPT, niche or settings.niche)},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Проанализируй изображение конкурента: визуальный стиль и потенциал анимации.",
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_base64}",
                            },
                        },
                    ],
                },
            ],
            temperature=0.4,
            max_tokens=1800,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or ""
        return image_from_json(self._parse_json(content))

    async def analyze_page(
        self,
        image_base64: str,
        url: str,
        title: Optional[str],
        text: Optional[str],
        niche: str = "",
    ) -> CompetitorAnalysis:
        notes = [f"Адрес: {url}"]
        if title:
            notes.append(f"Заголовок вкладки: {title}")
        if text:
            notes.append(f"Видимый текст страницы:\n{text[:2500]}")
        response = await self.client.chat.completions.create(
            model=self.vision_model,
            messages=[
                {"role": "system", "content": prompt_for(PAGE_PROMPT, niche or settings.niche)},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Это скриншот страницы конкурента, снятый через Selenium. "
                                "Оцени текст, визуальный стиль и анимационный потенциал.\n\n"
                                + "\n".join(notes)
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{image_base64}"},
                        },
                    ],
                },
            ],
            temperature=0.4,
            max_tokens=1800,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or ""
        return competitor_from_json(self._parse_json(content), content)


def get_openai_service() -> OpenAIService:
    return OpenAIService()
