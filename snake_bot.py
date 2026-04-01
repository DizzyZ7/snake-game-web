import html
import logging
import os
import sqlite3
from contextlib import closing

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
)

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    filename="bot_errors.log",
)
logger = logging.getLogger(__name__)

DB_PATH = os.getenv("SCORES_DB_PATH", "scores.db")
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GAME_SHORT_NAME = "namisnake"
GAME_URL = "https://dizzyz7.github.io/snake-game-web/snake_game.html"


def init_db(db_path: str = DB_PATH) -> None:
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                score INTEGER NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user ON scores (user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_score ON scores (score)")


def get_db_connection() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def get_display_name(user) -> str:
    if user.username:
        return f"@{user.username}"

    parts = [part for part in (user.first_name, user.last_name) if part]
    return " ".join(parts) if parts else "Игрок"


def escape_text(value: str) -> str:
    return html.escape(value, quote=False)


init_db()


async def start(update: Update, context: CallbackContext) -> None:
    username = escape_text(get_display_name(update.effective_user))
    await update.message.reply_text(
        f"🐍 Привет, {username}!\n\n"
        "🔹 /play – начать игру\n"
        "🏆 /top – топ игроков\n"
        "✨ /mytop – ваши лучшие результаты\n"
        "🕒 /last – последние 10 игр",
        parse_mode="HTML",
    )


async def play(update: Update, context: CallbackContext) -> None:
    try:
        await update.message.reply_game(game_short_name=GAME_SHORT_NAME)
    except Exception as exc:
        logger.error("Play error: %s", exc, exc_info=True)
        await update.message.reply_text(
            "⚠️ Не удалось запустить игру. Проверьте настройку Game URL в BotFather."
        )


async def top_players(update: Update, context: CallbackContext) -> None:
    try:
        with closing(get_db_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT username, MAX(score) AS max_score
                FROM scores
                GROUP BY user_id
                ORDER BY max_score DESC, username ASC
                LIMIT 10
                """
            )
            top = cursor.fetchall()

        response = "🏆 <b>Топ игроков:</b>\n\n"
        if not top:
            response += "Пока нет результатов"
        else:
            response += "\n".join(
                f"{index + 1}. {escape_text(name)}: {score}"
                for index, (name, score) in enumerate(top)
            )

        await update.message.reply_text(response, parse_mode="HTML")
    except Exception as exc:
        logger.error("Top error: %s", exc, exc_info=True)
        await update.message.reply_text("⚠️ Ошибка загрузки рейтинга")


async def my_top(update: Update, context: CallbackContext) -> None:
    try:
        with closing(get_db_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT score, strftime('%d.%m.%Y', timestamp)
                FROM scores
                WHERE user_id = ?
                ORDER BY score DESC, timestamp DESC
                LIMIT 5
                """,
                (update.effective_user.id,),
            )
            scores = cursor.fetchall()

        if not scores:
            await update.message.reply_text("🎮 У вас пока нет результатов!")
            return

        response = (
            "✨ <b>Ваши лучшие результаты:</b>\n\n"
            + "\n".join(
                f"{index + 1}. {score} ({date})"
                for index, (score, date) in enumerate(scores)
            )
        )
        await update.message.reply_text(response, parse_mode="HTML")
    except Exception as exc:
        logger.error("MyTop error: %s", exc, exc_info=True)
        await update.message.reply_text("⚠️ Ошибка загрузки данных")


async def last_games(update: Update, context: CallbackContext) -> None:
    try:
        with closing(get_db_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT username, score, strftime('%d.%m.%Y %H:%M', timestamp)
                FROM scores
                ORDER BY timestamp DESC
                LIMIT 10
                """
            )
            games = cursor.fetchall()

        if not games:
            await update.message.reply_text("Пока нет сыгранных игр.")
            return

        response = (
            "🕒 <b>Последние игры:</b>\n\n"
            + "\n".join(
                f"• {escape_text(username)}: {score} ({date})"
                for username, score, date in games
            )
        )
        await update.message.reply_text(response, parse_mode="HTML")
    except Exception as exc:
        logger.error("LastGames error: %s", exc, exc_info=True)
        await update.message.reply_text("⚠️ Ошибка загрузки данных")


async def game_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query

    try:
        if getattr(query, "game_short_name", None) != GAME_SHORT_NAME:
            await query.answer()
            return

        if getattr(query, "game_score", None) is None:
            await query.answer(url=GAME_URL)
            return

        username = get_display_name(query.from_user)
        with closing(get_db_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO scores (user_id, username, score)
                VALUES (?, ?, ?)
                """,
                (query.from_user.id, username, query.game_score),
            )
            conn.commit()

        await query.answer()
        logger.info(
            "Stored score %s for user %s",
            query.game_score,
            query.from_user.id,
        )
    except Exception as exc:
        logger.error("Callback error: %s", exc, exc_info=True)
        try:
            await query.answer(text="Ошибка открытия игры", show_alert=True)
        except Exception:
            logger.exception("Failed to answer callback after callback error")


def main() -> None:
    if not TOKEN:
        logger.critical("Token not found! Check .env file")
        return

    try:
        app = Application.builder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("play", play))
        app.add_handler(CommandHandler("top", top_players))
        app.add_handler(CommandHandler("mytop", my_top))
        app.add_handler(CommandHandler("last", last_games))
        app.add_handler(CommandHandler("help", start))
        app.add_handler(CallbackQueryHandler(game_callback))

        logger.info("Bot started successfully")
        app.run_polling()
    except Exception as exc:
        logger.critical("Fatal error: %s", exc, exc_info=True)


if __name__ == "__main__":
    main()
