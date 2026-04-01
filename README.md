# Telegram Snake Game

Небольшой проект с HTML5-версией Snake и Telegram-ботом на `python-telegram-bot`. Бот запускает игру через Telegram Games и хранит результаты в локальной SQLite-базе, а фронтенд дополнительно показывает локальный топ в браузере через IndexedDB.

## Что внутри

- `snake_bot.py` - Telegram-бот, команды, обработка callback'ов и запись результатов в SQLite.
- `snake_game.html` - сама игра на HTML/CSS/JavaScript.
- `.env.example` - пример переменных окружения.
- `requirements.txt` - зависимости Python.

## Возможности

- команды `/start`, `/play`, `/top`, `/mytop`, `/last`
- локальное хранение результатов игры в браузере
- адаптация под мобильный экран
- пауза, ускорение игры и препятствия
- логирование ошибок в файл

## Быстрый старт

1. Клонируйте репозиторий:

   ```bash
   git clone https://github.com/DizzyZ7/telegram-snake-game.git
   cd telegram-snake-game/improved_snake_game
   ```

2. Создайте и активируйте виртуальное окружение:

   Windows PowerShell:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   macOS / Linux:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Установите зависимости:

   ```bash
   pip install -r requirements.txt
   ```

4. Создайте `.env` по примеру `.env.example` и укажите токен:

   ```env
   TELEGRAM_BOT_TOKEN=your_token_here
   ```

5. Запустите бота:

   ```bash
   python snake_bot.py
   ```

## Важное про деплой

- `snake_game.html` можно хостить на GitHub Pages.
- `snake_bot.py` должен работать на отдельной машине или сервере, где доступна сеть и хранится `scores.db`.
- Локальный топ внутри HTML-игры хранится в браузере игрока и не заменяет серверный рейтинг бота.

## Команды бота

| Команда | Описание |
| --- | --- |
| `/start` | Приветствие и список команд |
| `/play` | Запуск игры |
| `/top` | Топ игроков |
| `/mytop` | Лучшие результаты текущего пользователя |
| `/last` | Последние сыгранные партии |

## Перед публикацией на GitHub

- не коммитьте `.env`
- не коммитьте `scores.db`
- не коммитьте `bot_errors.log`
- проверьте, что `GAME_URL` в `snake_bot.py` указывает на реальный опубликованный `snake_game.html`
