# Telegram Snake Game (Improved)

This project contains an improved version of the classic Snake game integrated into a Telegram bot using the **python‑telegram‑bot** library.  
The bot serves an HTML5 game through Telegram's inline game platform and records users' scores in a local SQLite database.  
This repository improves upon the original implementation by fixing duplicated code, adding new gameplay features, improving code structure, and enhancing the overall user experience.

## Features

- **Python Bot with SQLite database** – stores scores with timestamps and provides commands to view top players, personal bests and recent games.
- **HTML5 Snake game** – includes on‑screen controls for mobile devices, wrap‑around edges, IndexedDB for local highscores, and integration with Telegram WebApp to identify the player.
- **New gameplay elements** – optional obstacles that appear as your score increases, speed increases every five points, and a pause/resume button.
- **Responsive design** – looks good on mobile devices thanks to flexbox layout and touch event support.
- **Robust logging** – all errors are logged to `bot_errors.log` for easier debugging.
- **Modular code** – duplicated code has been removed and helper functions are split into logical sections for readability and maintainability.

## Setup and Installation

1. **Clone the repository** and change into its directory:

   ```bash
   git clone https://github.com/DizzyZ7/telegram-snake-game.git
   cd telegram-snake-game/improved_snake_game
   ```

2. **Create a virtual environment** and install dependencies:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure your bot token**: create a `.env` file in the repository root (see `.env.example`) and set `TELEGRAM_BOT_TOKEN` to the token you received from [@BotFather](https://t.me/BotFather).

4. **Run the bot**:

   ```bash
   python snake_bot.py
   ```

   The bot will start polling for updates. Use `/start` in your Telegram chat with the bot to see available commands.

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Greets the user and shows available commands. |
| `/play` | Sends the Snake game to the user. |
| `/top` | Shows the top 10 players of all time. |
| `/mytop` | Shows your top 5 scores. |
| `/last` | Shows the last 10 games recorded. |

## Files

- **`snake_bot.py`** – main bot implementation; handles commands, interacts with SQLite database, and logs errors.
- **`snake_game.html`** – HTML5/JavaScript implementation of the Snake game with obstacles and pause/resume functionality. It is served by Telegram automatically when users tap the game.
- **`.env.example`** – sample environment file; copy to `.env` and fill in your bot token.
- **`requirements.txt`** – Python dependencies for the bot.

## License

This project is licensed under the MIT License. See the [LICENSE](../LICENSE) file for details.