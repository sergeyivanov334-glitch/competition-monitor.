"""Промпты JSON-ответов для ниши моушн-дизайна и интерфейсной анимации."""

import re

from backend.models.schemas import CompetitorAnalysis, ImageAnalysis

TEXT_PROMPT = """Ты — эксперт по конкурентному анализу в нише моушн-дизайна и интерфейсной анимации для SaaS.
Проанализируй текст конкурента и верни только JSON:
{
  "strengths": ["сильная сторона"],
  "weaknesses": ["слабая сторона"],
  "unique_offers": ["уникальное предложение"],
  "recommendations": ["рекомендация"],
  "summary": "краткое резюме",
  "conclusion": "заключение на момент анализа: позиция конкурента и что это значит для студии анимации",
  "design_score": 7,
  "animation_potential": 8,
  "animation_notes": "как конкурент использует или продаёт движение, риггинг, Lottie, интерактив"
}
design_score — целое число от 0 до 10, оценка визуального стиля по тексту и описанным приёмам.
animation_potential — целое число от 0 до 10: насколько сильна анимационная подача и спрос на неё в оффере.
В каждом массиве 3–5 конкретных пунктов. Пиши на русском языке."""

IMAGE_PROMPT = """Ты — эксперт по визуальному стилю и анимации интерфейсов.
Проанализируй изображение конкурента (лендинг, баннер или скриншот) и верни только JSON:
{
  "description": "что изображено",
  "marketing_insights": ["инсайт"],
  "design_score": 7,
  "visual_style_analysis": "разбор цвета, типографики, композиции и движения",
  "animation_potential": 8,
  "animation_notes": "где на макете заложена или уже читается анимация",
  "recommendations": ["рекомендация"]
}
design_score — целое число от 0 до 10, оценка визуального стиля.
animation_potential — целое число от 0 до 10: потенциал и сила анимации в этом макете.
В массивах 3–5 пунктов. Пиши на русском языке."""

PAGE_PROMPT = """Ты — эксперт по конкурентному анализу сайтов в нише моушн-дизайна и интерфейсной анимации.
Перед тобой скриншот и текст живой страницы конкурента. Верни только JSON:
{
  "strengths": ["сильная сторона"],
  "weaknesses": ["слабая сторона"],
  "unique_offers": ["уникальное предложение"],
  "recommendations": ["рекомендация"],
  "summary": "краткое резюме",
  "conclusion": "заключение на момент анализа одним абзацем",
  "design_score": 7,
  "animation_potential": 8,
  "animation_notes": "как страница показывает движение и интерактив"
}
design_score — целое число от 0 до 10, визуальный стиль страницы.
animation_potential — целое число от 0 до 10.
В каждом массиве 3–5 конкретных пунктов. Пиши на русском языке."""


def prompt_for(base: str, niche: str) -> str:
    niche = (niche or "").strip()
    if not niche:
        return base
    return (
        base
        + f"\nСфера заказчика анализа: {niche}. Оценивай конкурента именно в этой сфере."
    )


def clamp_score(value) -> int:
    if isinstance(value, str):
        match = re.search(r"\d+", value)
        if not match:
            return 0
        value = match.group(0)
    try:
        return max(0, min(10, int(value)))
    except (TypeError, ValueError):
        return 0


def as_list(value) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def competitor_from_json(data: dict, raw: str = "") -> CompetitorAnalysis:
    summary = str(data.get("summary") or "").strip() or (raw[:500] if not data else "")
    conclusion = str(data.get("conclusion") or "").strip()
    design = clamp_score(data.get("design_score", 0))
    motion = clamp_score(data.get("animation_potential", 0))
    if not conclusion and summary:
        conclusion = (
            f"{summary} Визуальный стиль {design}/10, потенциал анимации {motion}/10."
        )
    return CompetitorAnalysis(
        strengths=as_list(data.get("strengths")),
        weaknesses=as_list(data.get("weaknesses")),
        unique_offers=as_list(data.get("unique_offers")),
        recommendations=as_list(data.get("recommendations")),
        summary=summary,
        conclusion=conclusion,
        design_score=design,
        animation_potential=motion,
        animation_notes=str(data.get("animation_notes") or "").strip(),
    )


def image_from_json(data: dict) -> ImageAnalysis:
    design = data.get("design_score", data.get("visual_style_score", 0))
    style = data.get("visual_style_score", design)
    design_score = clamp_score(design)
    style_score = clamp_score(style if style is not None else design_score)
    if "design_score" not in data:
        design_score = style_score
    return ImageAnalysis(
        description=str(data.get("description") or "").strip(),
        marketing_insights=as_list(data.get("marketing_insights")),
        visual_style_score=style_score,
        visual_style_analysis=str(data.get("visual_style_analysis") or "").strip(),
        recommendations=as_list(data.get("recommendations")),
        design_score=design_score,
        animation_potential=clamp_score(data.get("animation_potential", 0)),
        animation_notes=str(data.get("animation_notes") or "").strip(),
    )
