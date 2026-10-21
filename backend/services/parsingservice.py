"""Сбор страниц конкурентов через Selenium и установленный Google Chrome."""

import asyncio
import time
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from backend.config import settings


@dataclass
class PageSnapshot:
    url: str
    title: Optional[str]
    h1: Optional[str]
    text: Optional[str]
    screenshot_png: bytes


class ParsingService:
    """Открывает публичную страницу в headless Chrome и забирает текст со скриншотом."""

    def __init__(self) -> None:
        self.timeout = settings.parser_timeout

    def normalize_url(self, url: str) -> str:
        url = url.strip()
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Укажите корректный адрес сайта")
        return url

    def capture_sync(self, url: str) -> tuple[Optional[PageSnapshot], Optional[str]]:
        try:
            target = self.normalize_url(url)
        except ValueError as exc:
            return None, str(exc)

        driver = None
        try:
            options = Options()
            options.page_load_strategy = "eager"
            options.add_argument("--headless=new")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1366,768")
            options.add_argument("--lang=ru-RU")
            options.add_argument(f"--user-agent={settings.parser_user_agent}")
            driver = webdriver.Chrome(options=options)
            driver.set_page_load_timeout(self.timeout)
            driver.get(target)
            WebDriverWait(driver, min(self.timeout, 20)).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(4)

            title = (driver.title or "").strip() or None
            headings = driver.find_elements(By.TAG_NAME, "h1")
            h1 = " ".join(headings[0].text.split()) if headings else None
            h1 = h1 or None
            body = driver.find_element(By.TAG_NAME, "body").text or ""
            text = " ".join(body.split())
            text = text[:4000] if text else None
            screenshot = driver.get_screenshot_as_png()
        except TimeoutException:
            return None, "Страница открывалась слишком долго"
        except WebDriverException as exc:
            return None, self._driver_message(exc)
        except Exception as exc:
            return None, f"Не удалось открыть страницу: {exc}"
        finally:
            if driver is not None:
                driver.quit()

        return PageSnapshot(
            url=target,
            title=title,
            h1=h1,
            text=text,
            screenshot_png=screenshot,
        ), None

    async def capture(self, url: str) -> tuple[Optional[PageSnapshot], Optional[str]]:
        return await asyncio.to_thread(self.capture_sync, url)

    @staticmethod
    def _driver_message(exc: WebDriverException) -> str:
        message = str(exc).splitlines()[0][:300]
        lowered = message.lower()
        if "chrome" in lowered or "session not created" in lowered or "chromedriver" in lowered:
            return (
                "Не удалось запустить Google Chrome через Selenium. "
                "Установите Chrome и повторите запрос. "
                f"Детали: {message}"
            )
        return f"Не удалось открыть страницу: {message}"


parsing_service = ParsingService()
