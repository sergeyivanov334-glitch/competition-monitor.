"""Запуск веб-приложения."""

import sys
from pathlib import Path

import uvicorn

from backend.config import settings

ROOT = Path(__file__).resolve().parent


def main() -> None:
    background = "--no-reload" in sys.argv
    options = {
        "host": settings.api_host,
        "port": settings.api_port,
        "reload": not background,
    }
    if background:
        options["log_config"] = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {"format": "%(asctime)s %(levelname)s %(message)s"},
            },
            "handlers": {
                "file": {
                    "class": "logging.FileHandler",
                    "filename": str(ROOT / "server.log"),
                    "encoding": "utf-8",
                    "formatter": "default",
                }
            },
            "loggers": {
                "uvicorn": {"handlers": ["file"], "level": "INFO"},
                "uvicorn.error": {"handlers": ["file"], "level": "INFO", "propagate": False},
                "uvicorn.access": {"handlers": ["file"], "level": "INFO", "propagate": False},
            },
        }
    uvicorn.run("backend.main:app", **options)


if __name__ == "__main__":
    main()
