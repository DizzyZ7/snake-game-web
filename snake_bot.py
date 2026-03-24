"""
Telegram Snake Game Bot (improved)
---------------------------------

This script implements a Telegram bot that serves an HTML5 Snake game via Telegram's game platform.
It records players' scores in a local SQLite database and exposes commands to view leaderboards and
personal statistics. The bot has been refactored to remove duplicate code, improve error handling,
and make the database interactions more robust.

Before running, ensure you have created a `.env` file with your Telegram bot token (see `.env.example`).
Install dependencies from `requirements.txt` and run the script with Python 3.8+.
"""

import os
import sqlite3
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackContext,
    CallbackQueryHandler
)


# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    filename='bot_errors.log'
)
logger = logging.getLogger(__name__)


def init_db(db_path: str = 'scores.db') -> None:
    """Initialise the SQLite database and create indexes if they do not exist."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            score INTEGER NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_user ON scores (user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_score ON scores (score)')
    conn.commit()
    conn.close()


def get_db_connection() -> sqlite3.Connection:
    """Return a new connection to the database with foreign keys enabled."""
    conn = sqlite3.connect('scores.db', isolation_level=None, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


# Initialise database on module import
init_db()

# Load token from environment
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


async def start(update: Update, context: CallbackContext) -> None:
    """Send a welcome message and list available commands."""
    user = update.effective_user
    username = f"@{user.username}" if user.username else user.first_name or 'Игрок'
    message = (
        f"🐍 Привет, {username}!\n\n"
        "🔹 /play – начать игру\n"
        "🏆 /top – топ игроков\n"
        "✨ /mytop – ваши лучшие результаты\n"
        "🕒 /last – последние 10 игр"
    )
    await update.message.reply_text(message, parse_mode='HTML')


async def play(update: Update, context: CallbackContext) -> None:
    """Send the Snake game to the user."""
    try:
        await update.message.reply_game(game_short_name="snake_game")
    except Exception as e:
        logger.error("Error starting game: %s", e, exc_info=True)
        await update.message.reply_text("⚠️ Ошибка запуска игры")


async def top_players(update: Update, context: CallbackContext) -> None:
    """Display the top 10 players by their highest score."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT username, MAX(score) AS max_score
            FROM scores
            GROUP BY user_id
            ORDER BY max_score DESC
            LIMIT 10
        ''')
        rows = cursor.fetchall()
        if not rows:
            response = "🏆 <b>Топ игроков:</b>\n\nПока нет результатов"
        else:
            lines = [f"{idx + 1}. {name}: {score}" for idx, (name, score) in enumerate(rows)]
            response = "🏆 <b>Топ игроков:</b>\n\n" + "\n".join(lines)
        await update.message.reply_text(response, parse_mode='HTML')
    except Exception as e:
        logger.error("Error fetching top players: %s", e, exc_info=True)
        await update.message.reply_text("⚠️ Ошибка загрузки рейтинга")
    finally:
        conn.close()


async def my_top(update: Update, context: CallbackContext) -> None:
    """Display the top 5 scores for the current user."""
    try:
        user_id = update.effective_user.id
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT score, strftime('%d.%m.%Y', timestamp)
            FROM scores
            WHERE user_id = ?
            ORDER BY score DESC
            LIMIT 5
        ''', (user_id,))
        rows = cursor.fetchall()
        if not rows:
            await update.message.reply_text("🎮 У вас пока нет результатов!")
            return
        lines = [f"{idx + 1}. {score} ({date})" for idx, (score, date) in enumerate(rows)]
        response = "✨ <b>Ваши лучшие результаты:</b>\n\n" + "\n".join(lines)
        await update.message.reply_text(response, parse_mode='HTML')
    except Exception as e:
        logger.error("Error fetching user top: %s", e, exc_info=True)
        await update.message.reply_text("⚠️ Ошибка загрузки данных")
    finally:
        conn.close()


async def last_games(update: Update, context: CallbackContext) -> None:
    """Show the last 10 recorded games with username, score and timestamp."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT username, score, strftime('%d.%m.%Y %H:%M', timestamp)
            FROM scores
            ORDER BY timestamp DESC
            LIMIT 10
        ''')
        rows = cursor.fetchall()
        if not rows:
            await update.message.reply_text("Пока нет сыгранных игр.")
            return
        lines = [f"• {username}: {score} ({date})" for username, score, date in rows]
        response = "🕒 <b>Последние игры:</b>\n\n" + "\n".join(lines)
        await update.message.reply_text(response, parse_mode='HTML')
    except Exception as e:
        logger.error("Error fetching last games: %s", e, exc_info=True)
        await update.message.reply_text("⚠️ Ошибка загрузки данных")
    finally:
        conn.close()


async def game_callback(update: Update, context: CallbackContext) -> None:
    """Handle the callback when a user finishes the game. Save the score to the database."""
    query = update.callback_query
    await query.answer()  # Acknowledge the callback to avoid loading spinner
    try:
        if query.game_short_name != "snake_game":
            return
        # The `game_score` attribute is set only when the score is posted back by Telegram
        score = getattr(query, 'game_score', None)
        if score is None:
            return
        user = query.from_user
        username = f"@{user.username}" if user.username else f"{user.first_name} {user.last_name or ''}".strip()
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO scores (user_id, username, score)
            VALUES (?, ?, ?)
        ''', (user.id, username, score))
        conn.commit()
        logger.info("Stored score %s for user %s", score, user.id)
    except Exception as e:
        logger.error("Error handling game callback: %s", e, exc_info=True)
    finally:
        if 'conn' in locals():
            conn.close()


def build_application() -> Application:
    """Create and configure the Application instance."""
    if not TOKEN:
        logger.critical("Telegram bot token not found! Please set TELEGRAM_BOT_TOKEN in your .env file.")
        raise SystemExit(1)
    app = Application.builder().token(TOKEN).build()
    # Register handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("play", play))
    app.add_handler(CommandHandler("top", top_players))
    app.add_handler(CommandHandler("mytop", my_top))
    app.add_handler(CommandHandler("last", last_games))
    app.add_handler(CallbackQueryHandler(game_callback))
    return app


def main() -> None:
    """Entry point for running the bot."""
    try:
        app = build_application()
        logger.info("Bot started successfully")
        app.run_polling()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.critical("Fatal error in main: %s", e, exc_info=True)


if __name__ == '__main__':
    main()