# EasyTrip backend + Mini App (обновлённая версия)

## Что синхронизируется с сервером
- Telegram-профиль пользователя
- XP и уровень
- Посещённые страны
- Полученные штампы (теперь сохраняются отдельно и не пропадают после перезапуска Mini App)
- Прогресс задания недели (до 3 отметок)
- Избранные направления: добавление и удаление

## API
- `GET /health` — статус сервиса
- `GET /api/profile` — профиль пользователя
- `POST /api/countries` — добавить страну (+150 XP)
- `POST /api/stamps` — получить штамп (+100 XP, защита от повторного начисления)
- `POST /api/mission` — отметить прогресс задания (+25 XP, максимум 3)
- `POST /api/xp?xp=...` — начислить XP (служебный endpoint)
- `GET/POST /api/favorites` — избранное
- `DELETE /api/favorites/{id}` — удалить из избранного

Все пользовательские API требуют заголовок `X-Telegram-Init-Data` и проверяют подпись Telegram.

## Render
В Render Environment должны быть:
- `BOT_TOKEN` — токен бота (секрет, не коммитить)
- `DATABASE_PATH` — `/var/data/easytrip.db`
- `ALLOWED_ORIGINS` — origin GitHub Pages Mini App, без завершающего `/`

В `render.yaml` настроен persistent disk `/var/data` (1 GB). Если тариф Render не поддерживает диск, SQLite будет временной и данные могут потеряться при redeploy.

## Mini App
Файл `easytrip-miniapp/index.html` — frontend. API URL задан в переменной `API` внутри файла.

## Важно
Проверена компиляция Python. Реальное Telegram-подключение, подпись initData и работа Render требуют теста в Telegram после deploy.
