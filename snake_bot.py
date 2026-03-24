import os
import sqlite3
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackContext,
    CallbackQueryHandler,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    filename="bot_errors.log",
)
logger = logging.getLogger(__name__)


def init_db(db_path: str = "scores.db") -> None:
    conn = sqlite3.connect(db_path)
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
    conn.commit()
    conn.close()


def get_db_connection() -> sqlite3.Connection:
    return sqlite3.connect("scores.db")


init_db()

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GAME_SHORT_NAME = "namisnake"
GAME_URL = "https://dizzyz7.github.io/snake-game-web/snake_game.html"


async def start(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    username = f"@{user.username}" if user.username else (user.first_name or "Игрок")
    await update.message.reply_text(
        f"🐍 Привет, {username}!\n\n"
        f"🔹 /play – начать игру\n"
        f"🏆 /top – топ игроков\n"
        f"✨ /mytop – ваши лучшие результаты\n"
        f"🕒 /last – последние 10 игр",
        parse_mode="HTML",
    )


async def play(update: Update, context: CallbackContext) -> None:
    try:
        await update.message.reply_game(game_short_name=GAME_SHORT_NAME)
    except Exception as e:
        logger.error("Play error: %s", e, exc_info=True)
        await update.message.reply_text(f"⚠️ Ошибка запуска игры: {e}")


async def top_players(update: Update, context: CallbackContext) -> None:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT username, MAX(score) as max_score
            FROM scores
            GROUP BY user_id
            ORDER BY max_score DESC
            LIMIT 10
            """
        )
        top = cursor.fetchall()

        response = "🏆 <b>Топ игроков:</b>\n\n"
        if not top:
            response += "Пока нет результатов"
        else:
            response += "\n".join(
                f"{i + 1}. {name}: {score}"
                for i, (name, score) in enumerate(top)
            )

        await update.message.reply_text(response, parse_mode="HTML")
    except Exception as e:
        logger.error("Top error: %s", e, exc_info=True)
        await update.message.reply_text("⚠️ Ошибка загрузки рейтинга")
    finally:
        if conn:
            conn.close()


async def my_top(update: Update, context: CallbackContext) -> None:
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT score, strftime('%d.%m.%Y', timestamp)
            FROM scores
            WHERE user_id = ?
            ORDER BY score DESC
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
                f"{i + 1}. {score} ({date})"
                for i, (score, date) in enumerate(scores)
            )
        )

        await update.message.reply_text(response, parse_mode="HTML")
    except Exception as e:
        logger.error("MyTop error: %s", e, exc_info=True)
        await update.message.reply_text("⚠️ Ошибка загрузки данных")
    finally:
        if conn:
            conn.close()


async def last_games(update: Update, context: CallbackContext) -> None:
    conn = None
    try:
        conn = get_db_connection()
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
                f"• {username}: {score} ({date})"
                for username, score, date in games
            )
        )

        await update.message.reply_text(response, parse_mode="HTML")
    except Exception as e:
        logger.error("LastGames error: %s", e, exc_info=True)
        await update.message.reply_text("⚠️ Ошибка загрузки данных")
    finally:
        if conn:
            conn.close()


async def game_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    conn = None

    try:
        if (
            getattr(query, "game_short_name", None) == GAME_SHORT_NAME
            and getattr(query, "game_score", None) is None
        ):
            await query.answer(url=GAME_URL)
            return

        if (
            getattr(query, "game_short_name", None) == GAME_SHORT_NAME
            and getattr(query, "game_score", None) is not None
        ):
            user = query.from_user
            username = (
                f"@{user.username}"
                if user.username
                else f"{user.first_name} {user.last_name or ''}".strip()
            )

            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO scores (user_id, username, score)
                VALUES (?, ?, ?)
                """,
                (user.id, username, query.game_score),
            )
            conn.commit()

            await query.answer()
            logger.info("Stored score %s for user %s", query.game_score, user.id)
            return

        await query.answer()

    except Exception as e:
        logger.error("Callback error: %s", e, exc_info=True)
        try:
            await query.answer(text="Ошибка открытия игры", show_alert=True)
        except Exception:
            pass
    finally:
        if conn:
            conn.close()


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
    except Exception as e:
        logger.critical("Fatal error: %s", e, exc_info=True)


if __name__ == "__main__":
    main()