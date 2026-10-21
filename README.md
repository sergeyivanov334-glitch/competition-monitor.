# Competition Monitor

Отдельное приложение на базе кода урока: следит за сайтами конкурентов в нише **моушн-дизайна и интерфейсной анимации для SaaS**. Ветка репозитория: `competition-monitor`.

Пользователь указывает 3–5 сайтов. Приложение сразу даёт заключение по параметрам из промптов: `design_score` (0–10, визуальный стиль), `animation_potential` (0–10), сильные и слабые стороны, уникальные предложения, рекомендации. Пока открыты десктоп или сервер, проверка повторяется раз в сутки. Если заголовок, H1 или видимый текст изменились, отличие и дата появляются в отдельном поле «Изменения». Повторная формулировка модели при той же странице туда не пишется.

Кейс: [Rive](https://rive.app), [LottieFiles](https://lottiefiles.com), [Jitter](https://jitter.video), [School of Motion](https://www.schoolofmotion.com). Бриф, список и схемы лендингов лежат в `data/`.

## Запуск

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python run.py
```

Откройте http://127.0.0.1:8090

В `.env` укажите ключ и не коммитьте этот файл:

- `LLM_PROVIDER=openai` и `OPENAI_API_KEY`
- либо `LLM_PROVIDER=proxy`, `PROXY_API` и при необходимости `PROXY_BASE_URL`

Проверка эндпоинтов: `POST /analyzetext`, `POST /analyzeimage`, `POST /parsedemo` (те же методы доступны как `/analyze_text`, `/analyze_image`, `/parse_demo`). Список сайтов и обход: `GET /monitor`, `POST /monitor/run`.

Нужен установленный Google Chrome: страницы снимает Selenium.

## Десктоп

```bash
pip install -r requirements.txt
pip install -r desktop/requirements.txt
python build.py
```

Файл: `desktop/dist/competitionmonitor/competitionmonitor.exe`. Рядом положите свой `.env`. Окно можно не закрывать: таймер раз в сутки сравнивает сохранённые сайты. Если приложение было закрыто дольше суток, проверка стартует при следующем запуске.

В этой сборке PyInstaller для Python 3.14 нет оконного загрузчика, поэтому рядом с окном видна консоль. На работу мониторинга это не влияет.

## Что намеренно не в репозитории

Ключ API, `.env`, `history.json`, `monitor_state.json`, сборка PyInstaller.
