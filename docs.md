# Документация API

Приложение состоит из FastAPI-бэкенда и одной страницы `frontend/index.html`.

## Структура

```
backend/config.py                  настройки и путь к history.json
backend/main.py                    эндпоинты
backend/models/schemas.py          схемы запросов и ответов
backend/services/openaiservice.py   промпты: design_score и animation_potential
backend/services/openai_service.py   запросы к модели
backend/services/parsingservice.py   Selenium: снимок страницы конкурента
backend/services/parser_service.py   совместимый вызов парсера
backend/services/monitor_service.py  сайты, суточное сравнение, даты изменений
backend/services/history_service.py  последние 10 записей
frontend/                          страница, стили и клиент
run.py                             запуск uvicorn
```

## Эндпоинты

Все ответы — JSON.

### POST /analyze_text

```json
{ "text": "Текст конкурента длиннее 10 символов" }
```

```json
{
  "success": true,
  "analysis": {
    "strengths": ["..."],
    "weaknesses": ["..."],
    "unique_offers": ["..."],
    "recommendations": ["..."],
    "summary": "...",
    "conclusion": "...",
    "design_score": 7,
    "animation_potential": 8,
    "animation_notes": "..."
  }
}
```

Те же тела принимает `POST /analyzetext`.

### POST /analyze_image

`multipart/form-data`, поле `file`. Допустимы PNG, JPG, GIF, WEBP до 10 МБ.

```json
{
  "success": true,
  "analysis": {
    "description": "...",
    "marketing_insights": ["..."],
    "visual_style_score": 7,
    "visual_style_analysis": "...",
    "recommendations": ["..."],
    "design_score": 7,
    "animation_potential": 8,
    "animation_notes": "..."
  }
}
```

Тот же запрос принимает `POST /analyzeimage`.

### POST /parse_demo

```json
{ "url": "https://example.com" }
```

`POST /parsedemo` делает то же самое.

Selenium запускает установленный Google Chrome в фоне, открывает адрес, снимает видимую область и передаёт скриншот вместе с текстом в модель. В ответе есть `screenshot` — PNG в base64. Успешный разбор пишется в историю.

Адреса кейса заданы в `backend/config.py` (`competitor_urls`). Пользователь может заменить их в форме.

### GET /monitor

Текущая ниша, сайты, заключение по каждому и список изменений с датой.

### POST /monitor/run

```json
{ "urls": ["https://rive.app"], "niche": "Моушн-дизайн" }
```

Сразу анализирует переданные сайты (от 1 до 5). Следующий автоматический обход — через 24 часа, если запущены сервер или десктоп. В «Изменения» попадает только отличие содержимого страницы, не новый пересказ той же версии.

### GET /history

Последние 10 записей: тип (`text`, `image`, `parse`), краткое содержание запроса и ответа, время.

### DELETE /history

Очищает `history.json`.

### GET /health

Проверка, что сервис запущен.

## Мультимодальность

Текст и страница идут в чат-модель как обычное сообщение. Изображение передаётся как `image_url` с data-URL. Модель просят вернуть JSON, интерфейс раскладывает поля по блокам.
