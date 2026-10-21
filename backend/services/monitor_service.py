"""Список сайтов конкурентов, снимок параметров и ежедневное сравнение."""

import base64
import hashlib
import json
import os
import uuid
from datetime import datetime, timedelta
from typing import Optional

from backend.config import settings
from backend.models.schemas import CompetitorAnalysis, MonitorStateResponse
from backend.services.history_service import history_service
from backend.services.openai_service import get_openai_service
from backend.services.parsingservice import parsing_service

CHECK_INTERVAL = timedelta(hours=settings.monitor_interval_hours)
LOCK_STALE = timedelta(minutes=30)


def content_hash(title: Optional[str], h1: Optional[str], text: Optional[str]) -> str:
    raw = "\n".join(
        [
            (title or "").strip().lower(),
            (h1 or "").strip().lower(),
            " ".join((text or "").split()).lower(),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def diff_snapshots(previous: dict, current: dict) -> list[dict]:
    """Отличия параметров. Пустой список, если текст и заголовки не менялись."""
    if previous.get("content_hash") and previous.get("content_hash") == current.get("content_hash"):
        return []

    items: list[dict] = []

    def add(field: str, before, after) -> None:
        before_text = "" if before is None else str(before).strip()
        after_text = "" if after is None else str(after).strip()
        if before_text == after_text:
            return
        items.append({"field": field, "before": before_text, "after": after_text})

    add("Заголовок", previous.get("title"), current.get("title"))
    add("H1", previous.get("h1"), current.get("h1"))
    add("Текст страницы", previous.get("text_excerpt"), current.get("text_excerpt"))
    previous_analysis = previous.get("analysis") or {}
    current_analysis = current.get("analysis") or {}
    add("Оценка дизайна", previous_analysis.get("design_score"), current_analysis.get("design_score"))
    add(
        "Потенциал анимации",
        previous_analysis.get("animation_potential"),
        current_analysis.get("animation_potential"),
    )
    add("Резюме", previous_analysis.get("summary"), current_analysis.get("summary"))
    if not items:
        items.append(
            {
                "field": "Страница",
                "before": "предыдущий снимок",
                "after": "содержимое страницы изменилось",
            }
        )
    return items


class MonitorService:
    def __init__(self) -> None:
        self.path = settings.monitor_path
        self.lock_path = self.path.with_suffix(".lock")

    def _empty(self) -> dict:
        return {
            "niche": settings.niche,
            "urls": [],
            "last_run_at": None,
            "next_run_at": None,
            "sites": {},
            "changes": [],
        }

    def _load(self) -> dict:
        if not self.path.exists():
            return self._empty()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return self._empty()
        if not isinstance(data, dict):
            return self._empty()
        base = self._empty()
        base.update({key: data.get(key, base[key]) for key in base})
        if not isinstance(base["sites"], dict):
            base["sites"] = {}
        if not isinstance(base["changes"], list):
            base["changes"] = []
        if not isinstance(base["urls"], list):
            base["urls"] = []
        return base

    def _save(self, state: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.path)

    def normalize_urls(self, urls: list[str]) -> list[str]:
        cleaned: list[str] = []
        for url in urls:
            if not str(url).strip():
                continue
            normalized = parsing_service.normalize_url(str(url))
            if normalized not in cleaned:
                cleaned.append(normalized)
        if not cleaned:
            raise ValueError("Укажите хотя бы один сайт конкурента")
        if len(cleaned) > 5:
            raise ValueError("Можно следить не больше чем за 5 сайтами")
        return cleaned

    def save_sites(self, urls: list[str], niche: Optional[str] = None) -> dict:
        state = self._load()
        state["urls"] = self.normalize_urls(urls)
        if niche is not None and niche.strip():
            state["niche"] = niche.strip()
        elif not state.get("niche"):
            state["niche"] = settings.niche
        self._save(state)
        return state

    def is_due(self, now: Optional[datetime] = None) -> bool:
        state = self._load()
        if not state["urls"] or not state.get("last_run_at"):
            return False
        moment = now or datetime.now()
        try:
            last_run = datetime.fromisoformat(state["last_run_at"])
        except ValueError:
            return True
        return moment - last_run >= CHECK_INTERVAL

    def public_state(self) -> dict:
        state = self._load()
        urls = list(state["urls"])
        sites = []
        for url in urls:
            sites.append(self._site_view(url, state["sites"].get(url)))
        payload = MonitorStateResponse(
            niche=state.get("niche") or settings.niche,
            urls=urls,
            defaults=settings.competitor_url_list,
            last_run_at=state.get("last_run_at"),
            next_run_at=state.get("next_run_at"),
            sites=sites,
            changes=state.get("changes") or [],
        )
        return payload.model_dump()

    async def run(
        self,
        urls: Optional[list[str]] = None,
        niche: Optional[str] = None,
        scheduled: bool = False,
    ) -> dict:
        if urls is not None:
            self.save_sites(urls, niche)
        elif niche:
            state = self._load()
            state["niche"] = niche.strip() or state.get("niche") or settings.niche
            self._save(state)

        state = self._load()
        if not state["urls"]:
            raise ValueError("Сначала добавьте сайты конкурентов")

        try:
            with self._locked(scheduled):
                return await self._run_locked(state["urls"], state.get("niche") or settings.niche)
        except RuntimeError as exc:
            if scheduled and str(exc) == "scheduled-skip":
                return self.public_state()
            raise

    async def _run_locked(self, urls: list[str], niche: str) -> dict:
        service = get_openai_service()
        state = self._load()
        now = datetime.now().isoformat(timespec="seconds")
        fresh_changes = 0

        for url in urls:
            previous = state["sites"].get(url)
            try:
                site, change = await self._inspect(service, url, niche, previous, now)
            except Exception as exc:
                site = dict(previous or {"url": url})
                site["url"] = url
                site["error"] = f"Проверка не выполнена: {exc}"
                change = None
            state["sites"][url] = site
            if change:
                state["changes"].insert(0, change)
                fresh_changes += 1

        state["changes"] = state["changes"][:100]
        state["last_run_at"] = now
        state["next_run_at"] = (datetime.now() + CHECK_INTERVAL).isoformat(timespec="seconds")
        state["niche"] = niche
        self._save(state)
        history_service.add_entry(
            request_type="monitor",
            request_summary=f"Обход {len(urls)} сайтов",
            response_summary=f"Изменений: {fresh_changes}. Ниша: {niche}",
        )
        return self.public_state()

    async def _inspect(self, service, url: str, niche: str, previous: Optional[dict], now: str):
        snapshot, error = await parsing_service.capture(url)
        if error or snapshot is None:
            site = dict(previous or {"url": url})
            site["url"] = url
            site["error"] = error or "Страница не открылась"
            return site, None

        excerpt = (snapshot.text or "")[:400]
        digest = content_hash(snapshot.title, snapshot.h1, snapshot.text)
        if previous and previous.get("content_hash") == digest and previous.get("analysis"):
            site = dict(previous)
            site.update(
                {
                    "url": snapshot.url,
                    "title": snapshot.title,
                    "h1": snapshot.h1,
                    "text_excerpt": excerpt,
                    "error": None,
                    "checked_at": now,
                }
            )
            return site, None

        analysis = await service.analyze_page(
            image_base64=base64.b64encode(snapshot.screenshot_png).decode("ascii"),
            url=snapshot.url,
            title=snapshot.title,
            text=snapshot.text,
            niche=niche,
        )
        site = self._site_record(snapshot.url, snapshot.title, snapshot.h1, excerpt, digest, analysis, now)
        change = None
        if previous and previous.get("analysis"):
            items = diff_snapshots(previous, site)
            if items:
                change = {
                    "id": str(uuid.uuid4()),
                    "url": snapshot.url,
                    "changed_at": now,
                    "items": items,
                }
        return site, change

    @staticmethod
    def _site_record(
        url: str,
        title: Optional[str],
        h1: Optional[str],
        excerpt: str,
        digest: str,
        analysis: CompetitorAnalysis,
        now: str,
    ) -> dict:
        payload = analysis.model_dump()
        return {
            "url": url,
            "title": title,
            "h1": h1,
            "text_excerpt": excerpt,
            "content_hash": digest,
            "analyzed_at": now,
            "checked_at": now,
            "error": None,
            "conclusion": payload.get("conclusion") or payload.get("summary") or "",
            "analysis": payload,
        }

    @staticmethod
    def _site_view(url: str, raw: Optional[dict]) -> dict:
        raw = raw or {}
        analysis = raw.get("analysis") or {}
        has_analysis = bool(analysis)
        return {
            "url": raw.get("url") or url,
            "title": raw.get("title"),
            "h1": raw.get("h1"),
            "analyzed_at": raw.get("analyzed_at"),
            "conclusion": raw.get("conclusion") or analysis.get("conclusion") or "",
            "design_score": analysis.get("design_score") if has_analysis else None,
            "animation_potential": analysis.get("animation_potential") if has_analysis else None,
            "animation_notes": analysis.get("animation_notes") or "",
            "summary": analysis.get("summary") or "",
            "strengths": analysis.get("strengths") or [],
            "weaknesses": analysis.get("weaknesses") or [],
            "unique_offers": analysis.get("unique_offers") or [],
            "recommendations": analysis.get("recommendations") or [],
            "error": raw.get("error"),
        }

    def _locked(self, scheduled: bool):
        return _FileLock(self.lock_path, scheduled)


class _FileLock:
    def __init__(self, path, scheduled: bool) -> None:
        self.path = path
        self.scheduled = scheduled
        self.handle = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._clear_stale()
        try:
            self.handle = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_RDWR)
        except FileExistsError as exc:
            if self.scheduled:
                raise RuntimeError("scheduled-skip") from exc
            raise RuntimeError("Анализ уже выполняется") from exc
        os.write(self.handle, str(os.getpid()).encode("ascii"))
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.handle is not None:
            os.close(self.handle)
            self.handle = None
        try:
            self.path.unlink(missing_ok=True)
        except OSError:
            pass

    def _clear_stale(self) -> None:
        if not self.path.exists():
            return
        try:
            age = datetime.now() - datetime.fromtimestamp(self.path.stat().st_mtime)
        except OSError:
            return
        if age >= LOCK_STALE:
            try:
                self.path.unlink()
            except OSError:
                pass


monitor_service = MonitorService()
