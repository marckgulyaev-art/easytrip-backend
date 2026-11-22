# EasyTrip API — первый backend

## Что умеет
- Проверяет Telegram Mini App `initData` подписью с токеном бота.
- Создаёт/обновляет профиль Telegram-пользователя.
- Хранит профиль, XP и посещённые страны в SQLite.
- `GET /health` — проверка сервиса.
- `GET /api/profile` — профиль пользователя (требует `X-Telegram-Init-Data`).
- `POST /api/countries` — добавление страны (требует Telegram initData).

## Размещение на Render
1. Создай GitHub-репозиторий для backend или загрузи папку `backend` в репозиторий EasyTrip.
2. На Render выбери **New → Blueprint** и подключи репозиторий, в котором есть `backend/render.yaml`.
3. При создании сервиса Render запросит `BOT_TOKEN`. Вставь токен из своего локального `.env` (никому его не отправляай и не коммить).
4. Дождись статуса Live и проверь URL `/health`.
5. Скопируй HTTPS URL сервиса. Его нужно вставить в `API_BASE` в `miniapp/index.html` вместо пустой строки.
6. Commit/push обновлённый `miniapp/index.html` в GitHub Pages. После обновления открой Mini App заново.

SQLite размещена на persistent disk `/var/data/easytrip.db`. Если Render не предоставляет постоянный диск на выбранном тарифе, данные могут сбрасываться после перезапуска — обязательно проверь наличие диска в настройках.
