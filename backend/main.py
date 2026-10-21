"""FastAPI: мониторинг сайтов конкурентов."""

import asyncio
import base64
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.models.schemas import (
    HistoryResponse,
    ImageAnalysisResponse,
    MonitorRunRequest,
    MonitorStateResponse,
    ParseDemoRequest,
    ParseDemoResponse,
    ParsedContent,
    TextAnalysisRequest,
    TextAnalysisResponse,
)
from backend.services.history_service import history_service
from backend.services.monitor_service import monitor_service
from backend.services.openai_service import get_openai_service
from backend.services.parser_service import parser_service

logger = logging.getLogger("competitionmonitor")


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    task = asyncio.create_task(_daily_monitor())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


async def _daily_monitor() -> None:
    await asyncio.sleep(8)
    while True:
        try:
            if monitor_service.is_due():
                await monitor_service.run(scheduled=True)
        except Exception:
            logger.exception("Ежедневная проверка не выполнена")
        await asyncio.sleep(3600)

ALLOWED_IMAGE_TYPES = {
    "image/jpeg": "image/jpeg",
    "image/jpg": "image/jpeg",
    "image/png": "image/png",
    "image/gif": "image/gif",
    "image/webp": "image/webp",
}

app = FastAPI(
    title="Competition Monitor",
    description="Анализ сайтов конкурентов в нише моушн-дизайна и ежедневное сравнение",
    version="1.0.0",
    lifespan=_lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _clip(text: str, limit: int) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Competition Monitor", "version": "1.0.0"}


@app.post("/analyze_text", response_model=TextAnalysisResponse)
async def analyze_text(request: TextAnalysisRequest):
    try:
        service = get_openai_service()
        analysis = await service.analyze_text(request.text)
        history_service.add_entry(
            request_type="text",
            request_summary=_clip(request.text, 180),
            response_summary=analysis.summary or "Анализ текста выполнен",
        )
        return TextAnalysisResponse(success=True, analysis=analysis)
    except Exception as exc:
        return TextAnalysisResponse(success=False, error=str(exc))


@app.post("/analyze_image", response_model=ImageAnalysisResponse)
async def analyze_image(file: UploadFile = File(...)):
    mime = ALLOWED_IMAGE_TYPES.get((file.content_type or "").lower())
    if not mime:
        raise HTTPException(
            status_code=400,
            detail="Нужен файл PNG, JPG, GIF или WEBP",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Файл пустой")
    if len(content) > settings.max_image_bytes:
        raise HTTPException(status_code=400, detail="Файл больше 10 МБ")

    try:
        service = get_openai_service()
        analysis = await service.analyze_image(
            image_base64=base64.b64encode(content).decode("ascii"),
            mime_type=mime,
        )
        history_service.add_entry(
            request_type="image",
            request_summary=f"Изображение: {file.filename or 'file'}",
            response_summary=analysis.description or "Анализ изображения выполнен",
        )
        return ImageAnalysisResponse(success=True, analysis=analysis)
    except Exception as exc:
        return ImageAnalysisResponse(success=False, error=str(exc))


@app.post("/parse_demo", response_model=ParseDemoResponse)
async def parse_demo(request: ParseDemoRequest):
    try:
        snapshot, error = await parser_service.capture(request.url)
        if error or snapshot is None:
            return ParseDemoResponse(success=False, error=error or "Страница не открылась")

        service = get_openai_service()
        analysis = await service.analyze_page(
            image_base64=base64.b64encode(snapshot.screenshot_png).decode("ascii"),
            url=snapshot.url,
            title=snapshot.title,
            text=snapshot.text,
        )
        data = ParsedContent(
            url=snapshot.url,
            title=snapshot.title,
            h1=snapshot.h1,
            first_paragraph=(snapshot.text or "")[:500] or None,
            screenshot=base64.b64encode(snapshot.screenshot_png).decode("ascii"),
            analysis=analysis,
        )
        history_service.add_entry(
            request_type="parse",
            request_summary=f"URL: {data.url}",
            response_summary=snapshot.title or analysis.summary or "Страница разобрана",
        )
        return ParseDemoResponse(success=True, data=data)
    except Exception as exc:
        return ParseDemoResponse(success=False, error=str(exc))


@app.get("/history", response_model=HistoryResponse)
async def get_history():
    items = history_service.get_history()
    return HistoryResponse(items=items, total=len(items))


@app.delete("/history")
async def clear_history():
    history_service.clear_history()
    return {"success": True, "message": "История очищена"}


@app.get("/monitor", response_model=MonitorStateResponse)
async def monitor_state():
    return monitor_service.public_state()


@app.post("/monitor/run", response_model=MonitorStateResponse)
async def monitor_run(request: MonitorRunRequest):
    try:
        return await monitor_service.run(urls=request.urls, niche=request.niche)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


app.add_api_route(
    "/analyzetext",
    analyze_text,
    methods=["POST"],
    response_model=TextAnalysisResponse,
)
app.add_api_route(
    "/analyzeimage",
    analyze_image,
    methods=["POST"],
    response_model=ImageAnalysisResponse,
)
app.add_api_route(
    "/parsedemo",
    parse_demo,
    methods=["POST"],
    response_model=ParseDemoResponse,
)


frontend = settings.frontend_dir


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    icon = frontend / "favicon.ico"
    if not icon.exists():
        raise HTTPException(status_code=404, detail="favicon.ico не найден")
    return FileResponse(icon, media_type="image/x-icon")


@app.get("/")
async def root():
    index = frontend / "index.html"
    if not index.exists():
        raise HTTPException(status_code=404, detail="frontend/index.html не найден")
    return FileResponse(index)


if frontend.exists():
    app.mount("/static", StaticFiles(directory=str(frontend)), name="static")
