#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import logging
import random
import re
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import aiosqlite

# ========== ТОКЕНЫ ==========
MAIN_TOKEN = "8734345661:AAEGNWbbMCqnPrhY7xAI3JKkPkUtDXCYJGY"
LOGGER_TOKEN = "8742280719:AAG4agCIdRqU2_M81vgYz3sdY5kJZaYNjq0"

# ========== ВАШИ ДАННЫЕ ==========
ADMIN_ID = 798224858
ADMIN_CHAT_ID = 798224858

# ========== ТРИ ВАШИХ GIF ==========
GIF_LIST = [
    "https://media.tenor.com/vOgdsVDn8SQAAAAM/swpa.gif",
    "https://i.pinimg.com/originals/af/29/61/af2961e497cc845666209034991b52cd.gif",
    "https://giffiles.alphacoders.com/345/34554.gif"
]

# ========== ЛОГИРОВАНИЕ ==========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ========== БАЗА ДАННЫХ ==========
class Database:
    def __init__(self):
        self.db_path = "users.db"

    async def init(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    is_allowed INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS pending (
                    user_id INTEGER PRIMARY KEY,
                    msg_id INTEGER,
                    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()
        logger.info("✅ База данных инициализирована")

    async def set_allowed(self, user_id: int, allowed: bool):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO users (user_id, is_allowed) VALUES (?, ?)",
                (user_id, 1 if allowed else 0)
            )
            await db.commit()

    async def is_allowed(self, user_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cur = await db.execute(
                "SELECT is_allowed FROM users WHERE user_id = ?", 
                (user_id,)
            )
            row = await cur.fetchone()
            return row and row[0] == 1

    async def save_pending(self, user_id: int, msg_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO pending (user_id, msg_id) VALUES (?, ?)",
                (user_id, msg_id)
            )
            await db.commit()

    async def remove_pending(self, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM pending WHERE user_id = ?", 
                (user_id,)
            )
            await db.commit()

db = Database()

# ========== БОТЫ ==========
main_bot = Bot(token=MAIN_TOKEN)
main_dp = Dispatcher()
logger_bot = Bot(token=LOGGER_TOKEN)
logger_dp = Dispatcher()

# ========== КЛАВИАТУРА ==========
def get_main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌾 Запустить ферму", callback_data="farm")],
        [
            InlineKeyboardButton(text="🆘 Помощь", callback_data="help"),
            InlineKeyboardButton(text="ℹ️ О боте", callback_data="about")
        ]
    ])

# ========== ТЕКСТЫ ==========
WELCOME_TEXT = (
    "⚜️ *Добро пожаловать в бота для Hay Day*\n\n"
    "👤 Для получения доступа необходимо подтверждение администратора.\n\n"
    "Используйте меню ниже для навигации."
)

FARM_TEXT = (
    "🌾 *Бот для Hay Day запущен!*\n\n"
    "✅ Сбор урожая: активен\n"
    "✅ Посадка: активна\n"
    "✅ Магазин: проверка каждые 5 минут\n\n"
    "🛑 Для остановки используйте /stop"
)

HELP_TEXT = (
    "🆘 *Помощь*\n\n"
    "Если у вас возникли вопросы или проблемы, напишите сообщение ниже.\n"
    "Администратор получит его и ответит вам в ближайшее время."
)

ABOUT_TEXT = (
    "ℹ️ *О боте*\n\n"
    "**Hay Day Automation Bot**\n"
    "Версия: 2.0\n"
    "Разработчик: @alahovbabahov\n\n"
    "⚜️ *Код Гиас* — символ абсолютной силы\n\n"
    "Бот позволяет автоматизировать:\n"
    "• Сбор урожая\n"
    "• Посадку культур\n"
    "• Продажу в магазине"
)

# ========== ФУНКЦИЯ ОТПРАВКИ ГИФ ==========
async def send_gif_with_text(chat_id, text, keyboard=None):
    selected_gif = random.choice(GIF_LIST)
    try:
        await main_bot.send_animation(
            chat_id=chat_id,
            animation=selected_gif,
            caption=text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        return True
    except:
        await main_bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        return False

# ========== ОСНОВНОЙ БОТ ==========
@main_dp.message(Command("start"))
async def main_start(message: types.Message):
    user = message.from_user
    await db.set_allowed(user.id, False)
    
    await message.answer(
        WELCOME_TEXT,
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Разрешить", callback_data=f"allow_{user.id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"deny_{user.id}")
        ]
    ])
    
    request_text = (
        f"🔔 *Новый запрос на доступ*\n\n"
        f"👤 *Имя:* {user.full_name}\n"
        f"🆔 *ID:* `{user.id}`\n"
        f"🔗 *Username:* @{user.username if user.username else 'нет'}"
    )
    
    try:
        sent = await logger_bot.send_message(
            ADMIN_CHAT_ID,
            request_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        await db.save_pending(user.id, sent.message_id)
    except:
        pass

@main_dp.callback_query()
async def main_callbacks(callback: types.CallbackQuery):
    user = callback.from_user
    
    if callback.data not in ["help", "about"] and not await db.is_allowed(user.id):
        await callback.answer("⛔ У вас нет доступа", show_alert=True)
        return
    
    await callback.message.delete()
    
    if callback.data == "farm":
        await send_gif_with_text(user.id, FARM_TEXT)
        await logger_bot.send_message(
            ADMIN_CHAT_ID,
            f"🚜 Пользователь @{user.username} (ID: {user.id}) запустил ферму"
        )
    elif callback.data == "help":
        await send_gif_with_text(user.id, HELP_TEXT)
        await main_bot.send_message(user.id, "📝 Напишите ваше сообщение для администратора:")
    elif callback.data == "about":
        await send_gif_with_text(user.id, ABOUT_TEXT, get_main_keyboard())
    
    await callback.answer()

@main_dp.message()
async def forward_to_admin(message: types.Message):
    user = message.from_user
    
    if not await db.is_allowed(user.id):
        await message.answer("⛔ У вас нет доступа")
        return
    
    try:
        await logger_bot.send_message(
            ADMIN_CHAT_ID,
            f"📩 *Сообщение от пользователя*\n"
            f"👤 {user.full_name} (@{user.username})\n"
            f"🆔 ID: {user.id}\n"
            f"💬 Текст:\n{message.text}",
            parse_mode="Markdown"
        )
        await message.answer("✅ Сообщение отправлено администратору")
    except:
        await message.answer("❌ Ошибка отправки")

# ========== БОТ-ЛОГГЕР ==========
@logger_dp.message(Command("start"))
async def logger_start(message: types.Message):
    await message.answer(
        "👋 *Бот-логгер активен*\n\n"
        f"👤 Админ: @alahovbabahov\n"
        f"🆔 Chat ID: `{ADMIN_CHAT_ID}`",
        parse_mode="Markdown"
    )

@logger_dp.callback_query()
async def logger_callbacks(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Не для вас")
        return
    
    action, user_id_str = callback.data.split("_")
    user_id = int(user_id_str)
    
    if action == "allow":
        await db.set_allowed(user_id, True)
        await callback.message.edit_text(
            callback.message.text + "\n\n✅ *Доступ РАЗРЕШЁН*",
            parse_mode="Markdown"
        )
        try:
            await main_bot.send_message(
                user_id,
                "✅ *Доступ одобрен!*\n\nНажмите /start",
                parse_mode="Markdown"
            )
        except:
            pass
    else:
        await db.set_allowed(user_id, False)
        await callback.message.edit_text(
            callback.message.text + "\n\n❌ *Доступ ОТКАЗАН*",
            parse_mode="Markdown"
        )
        try:
            await main_bot.send_message(user_id, "❌ Доступ отклонён")
        except:
            pass
    
    await db.remove_pending(user_id)
    await callback.answer("✅ Готово")

@logger_dp.message()
async def admin_reply(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    if message.reply_to_message:
        match = re.search(r"ID: (\d+)", message.reply_to_message.text or "")
        if match:
            user_id = int(match.group(1))
            try:
                await main_bot.send_message(
                    user_id,
                    f"📨 *Ответ администратора:*\n{message.text}",
                    parse_mode="Markdown"
                )
                await message.reply("✅ Ответ отправлен")
            except:
                await message.reply("❌ Ошибка")

# ========== ЗАПУСК ==========
async def main():
    await db.init()
    
    print("=" * 60)
    print("🌾 HAY DAY BOT SYSTEM")
    print("=" * 60)
    print(f"👤 Админ: @alahovbabahov")
    print("=" * 60)
    
    await asyncio.gather(
        main_dp.start_polling(main_bot),
        logger_dp.start_polling(logger_bot)
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Боты остановлены")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
