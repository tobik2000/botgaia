import logging
import requests
import asyncio
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ChatMember
)
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    CallbackQueryHandler,
    filters
)

# ---------------------------------------
# ВСТАВЬ СВОИ КЛЮЧИ СЮДА
# ---------------------------------------
TOKEN = "8075897257:AAHQMSYww7LwC31Z6trEaBPRQtYI921mAoo"
DEEPSEEK_API_KEY = "sk-3d7df269a3db493190bce6b4d737acb1"
# ---------------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

game_active = False
game_round = 0
game_players = {}

# ---------------------------------------
# ФУНКЦИЯ: Генерация вопроса через DeepSeek
# ---------------------------------------
def generate_question():
    url = "https://api.deepseek.com/chat/completions"

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "system",
                "content": (
                    "Ты — шаманский ведущий. "
                    "Генерируй глубокие, атмосферные вопросы в стиле природы, духов, символов, "
                    "внутренних состояний. Вопрос должен быть коротким, но образным."
                )
            },
            {
                "role": "user",
                "content": "Создай новый вопрос для следующего раунда."
            }
        ]
    }

    response = requests.post(url, headers=headers, json=data).json()
    return response["choices"][0]["message"]["content"]


# ---------------------------------------
# КНОПКИ
# ---------------------------------------
ELEMENT_BUTTONS = InlineKeyboardMarkup([
    [InlineKeyboardButton("🔥 Огонь", callback_data="elem_огонь")],
    [InlineKeyboardButton("💧 Вода", callback_data="elem_вода")],
    [InlineKeyboardButton("🌿 Земля", callback_data="elem_земля")],
    [InlineKeyboardButton("🌬 Воздух", callback_data="elem_воздух")],
])

TOTEM_BUTTONS = InlineKeyboardMarkup([
    [InlineKeyboardButton("🐺 Волк", callback_data="totem_волк")],
    [InlineKeyboardButton("🦅 Орёл", callback_data="totem_орёл")],
    [InlineKeyboardButton("🐻 Медведь", callback_data="totem_медведь")],
    [InlineKeyboardButton("🦊 Лиса", callback_data="totem_лиса")],
    [InlineKeyboardButton("🦌 Олень", callback_data="totem_олень")],
])

DIRECTION_BUTTONS = InlineKeyboardMarkup([
    [InlineKeyboardButton("⬅ Налево", callback_data="dir_налево")],
    [InlineKeyboardButton("⬆ Прямо", callback_data="dir_прямо")],
    [InlineKeyboardButton("➡ Направо", callback_data="dir_направо")],
])


# ---------------------------------------
# Проверка: админ ли пользователь
# ---------------------------------------
async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    chat = update.effective_chat
    user = update.effective_user
    member = await chat.get_member(user.id)
    return member.status in (ChatMember.ADMINISTRATOR, ChatMember.OWNER)


# ---------------------------------------
# Старт игры
# ---------------------------------------
async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global game_active, game_round, game_players

    if not await is_admin(update, context):
        await update.effective_chat.send_message("Только администраторы могут начинать игру.")
        return

    if game_active:
        await update.effective_chat.send_message("Игра уже идёт.")
        return

    game_active = True
    game_round = 1
    game_players = {}

    await update.effective_chat.send_message(
        "🌿 Игра начинается.\n"
        "Погрузись в образы, символы и шёпот духов."
    )

    await ask_question(update)


# ---------------------------------------
# Выбор вопроса
# ---------------------------------------
async def ask_question(update: Update):
    global game_round

    if game_round % 3 == 0:
        await update.effective_chat.send_message("Какая стихия откликается тебе сейчас?", reply_markup=ELEMENT_BUTTONS)
        return

    if game_round % 5 == 0:
        await update.effective_chat.send_message("Какой дух‑тотем зовёт тебя?", reply_markup=TOTEM_BUTTONS)
        return

    if game_round % 7 == 0:
        await update.effective_chat.send_message("Куда ведёт твой путь?", reply_markup=DIRECTION_BUTTONS)
        return

    question = generate_question()
    await update.effective_chat.send_message(f"✨ Раунд {game_round}\n{question}")


# ---------------------------------------
# Завершение игры
# ---------------------------------------
async def stop_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global game_active, game_players

    if not await is_admin(update, context):
        await update.effective_chat.send_message("Только администраторы могут завершать игру.")
        return

    if not game_active:
        await update.effective_chat.send_message("Игра не идёт.")
        return

    game_active = False

    if not game_players:
        await update.effective_chat.send_message("Игра завершена. Никто не участвовал.")
        return

    winner = max(game_players, key=lambda uid: game_players[uid]["points"])
    wname = game_players[winner]["username"]
    wpoints = game_players[winner]["points"]

    text = ["🏁 Игра завершена!", "", "Результаты:"]
    for p in game_players.values():
        text.append(f"{p['username']}: {p['points']} баллов")

    text.append("")
    text.append(f"🏆 Победитель: *{wname}* ({wpoints} баллов)")

    await update.effective_chat.send_message("\n".join(text), parse_mode="Markdown")


# ---------------------------------------
# Обработка текстовых сообщений
# ---------------------------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global game_active, game_round, game_players

    text = update.message.text.lower()

    if "давай поиграем ботик" in text:
        await start_game(update, context)
        return

    if "хватит играть ботик" in text:
        await stop_game(update, context)
        return

    if not game_active:
        return

    user = update.message.from_user
    username = user.username or user.full_name or f"id_{user.id}"

    if user.id not in game_players:
        game_players[user.id] = {"username": username, "points": 0}

    game_players[user.id]["points"] += 1

    game_round += 1
    await ask_question(update)


# ---------------------------------------
# Обработка кнопок
# ---------------------------------------
async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global game_round, game_players

    query = update.callback_query
    await query.answer()

    user = query.from_user
    username = user.username or user.full_name or f"id_{user.id}"

    if user.id not in game_players:
        game_players[user.id] = {"username": username, "points": 0}

    game_players[user.id]["points"] += 1

    await query.edit_message_text(f"Ты выбрал: {query.data.split('_')[1]}")

    game_round += 1
    await ask_question(update)


# ---------------------------------------
# Запуск
# ---------------------------------------
import asyncio  # убедись, что этот импорт есть вверху файла

def main():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.add_handler(CallbackQueryHandler(handle_button))

    app.run_polling()


if __name__ == "__main__":
    main()
