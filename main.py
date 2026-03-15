#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
=====================================================
🌾 HAY DAY DUAL BOT SYSTEM - ГИФ ПРИ НАЖАТИИ КНОПОК
=====================================================
- При /start: только текст и меню (БЕЗ гифки)
- При нажатии на кнопки: сначала GIF, потом текст
- Три случайные гифки из вашего списка
=====================================================
"""

import asyncio
import logging
import random
import re
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import aiosqlite

# ========== ТОКЕНЫ ВАШИХ БОТОВ ==========
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

# ========== НАСТРОЙКА ЛОГИРОВАНИЯ ==========
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

# ========== ИНИЦИАЛИЗАЦИЯ БОТОВ ==========
main_bot = Bot(token=MAIN_TOKEN)
main_dp = Dispatcher()

logger_bot = Bot(token=LOGGER_TOKEN)
logger_dp = Dispatcher()

# ========== КЛАВИАТУРЫ ==========
def get_main_keyboard():
    """Главное меню с кнопками (БЕЗ ИНЛАЙН КНОПОК)"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌾 Запустить ферму", callback_data="farm")],
        [
            InlineKeyboardButton(text="🆘 Помощь", callback_data="help"),
            InlineKeyboardButton(text="ℹ️ О боте", callback_data="about")
        ]
    ])
    return keyboard

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

# ========== ФУНКЦИЯ ОТПРАВКИ ГИФ + ТЕКСТ ==========
async def send_gif_with_text(chat_id, text, keyboard=None):
    """Отправляет случайную GIF и под ней текст"""
    selected_gif = random.choice(GIF_LIST)
    logger.info(f"Отправка GIF: {selected_gif}")
    
    try:
        await main_bot.send_animation(
            chat_id=chat_id,
            animation=selected_gif,
            caption=text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        return True
    except Exception as e:
        logger.error(f"Ошибка отправки GIF: {e}")
        # Запасной вариант без GIF
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
    
    # ТОЛЬКО ТЕКСТ, БЕЗ ГИФКИ
    await message.answer(
        WELCOME_TEXT,
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )
    
    # Отправляем запрос на доступ админу
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
    except Exception as e:
        logger.error(f"Не удалось отправить запрос админу: {e}")

@main_dp.callback_query()
async def main_callbacks(callback: types.CallbackQuery):
    user = callback.from_user
    
    # Проверка доступа (кроме помощи и информации)
    if callback.data not in ["help", "about"] and not await db.is_allowed(user.id):
        await callback.answer(
            "⛔ У вас нет доступа. Ожидайте подтверждения администратора.", 
            show_alert=True
        )
        return
    
    # Удаляем старое сообщение с кнопками
    await callback.message.delete()
    
    if callback.data == "farm":
        # ГИФ + ТЕКСТ для фермы
        await send_gif_with_text(
            chat_id=user.id,
            text=FARM_TEXT
        )
        # Уведомляем админа
        await logger_bot.send_message(
            ADMIN_CHAT_ID,
            f"🚜 Пользователь @{user.username} (ID: {user.id}) запустил ферму"
        )
        
    elif callback.data == "help":
        # ГИФ + ТЕКСТ для помощи
        await send_gif_with_text(
            chat_id=user.id,
            text=HELP_TEXT
        )
        # Отправляем запрос на ввод сообщения
        await main_bot.send_message(
            chat_id=user.id,
            text="📝 Напишите ваше сообщение для администратора:"
        )
        
    elif callback.data == "about":
        # ГИФ + ТЕКСТ для информации
        await send_gif_with_text(
            chat_id=user.id,
            text=ABOUT_TEXT,
            keyboard=get_main_keyboard()
        )
    
    await callback.answer()

@main_dp.message()
async def forward_to_admin(message: types.Message):
    user = message.from_user
    
    if not await db.is_allowed(user.id):
        await message.answer(
            "⛔ У вас нет доступа. Используйте /start для запроса."
        )
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
        await message.answer(
            "✅ Сообщение отправлено администратору. Ожидайте ответа."
        )
    except Exception as e:
        logger.error(f"Ошибка пересылки сообщения: {e}")
        await message.answer(
            "❌ Не удалось отправить сообщение. Попробуйте позже."
        )

# ========== БОТ-ЛОГГЕР ==========
@logger_dp.message(Command("start"))
async def logger_start(message: types.Message):
    await message.answer(
        "👋 *Бот-логгер активен*\n\n"
        "**Сюда приходят:**\n"
        "• Запросы на доступ от новых пользователей\n"
        "• Уведомления о действиях\n"
        "• Сообщения из раздела Помощь\n\n"
        "**Как управлять:**\n"
        "• Нажимайте ✅ Разрешить / ❌ Отклонить на запросы\n"
        "• Отвечайте на сообщения через Reply\n\n"
        f"👤 Админ: @alahovbabahov\n"
        f"🆔 Chat ID: `{ADMIN_CHAT_ID}`",
        parse_mode="Markdown"
    )

@logger_dp.callback_query()
async def logger_callbacks(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔ Это не для вас")
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
                "✅ *Доступ одобрен!*\n\n"
                "Теперь вы можете использовать все функции бота.\n"
                "Нажмите /start для продолжения.",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Не удалось уведомить пользователя {user_id}: {e}")
            
    elif action == "deny":
        await db.set_allowed(user_id, False)
        await callback.message.edit_text(
            callback.message.text + "\n\n❌ *Доступ ОТКАЗАН*",
            parse_mode="Markdown"
        )
        try:
            await main_bot.send_message(
                user_id,
                "❌ Ваш запрос на доступ отклонён администратором."
            )
        except Exception as e:
            logger.error(f"Не удалось уведомить пользователя {user_id}: {e}")
    
    await db.remove_pending(user_id)
    await callback.answer("✅ Готово")

@logger_dp.message()
async def admin_reply(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    if message.reply_to_message:
        original_text = message.reply_to_message.text
        
        match = re.search(r"ID: (\d+)", original_text)
        if match:
            user_id = int(match.group(1))
            try:
                await main_bot.send_message(
                    user_id,
                    f"📨 *Ответ администратора:*\n{message.text}",
                    parse_mode="Markdown"
                )
                await message.reply("✅ Ответ отправлен пользователю.")
            except Exception as e:
                await message.reply(f"❌ Ошибка отправки: {e}")

# ========== ЗАПУСК ==========
async def main():
    await db.init()
    
    print("=" * 60)
    print("🌾 HAY DAY DUAL BOT SYSTEM")
    print("=" * 60)
    print(f"👤 Администратор: @alahovbabahov")
    print(f"🆔 Admin ID: {ADMIN_ID}")
    print("=" * 60)
    print("🎬 ЗАГРУЖЕННЫЕ GIF (для кнопок):")
    for i, gif in enumerate(GIF_LIST, 1):
        print(f"   {i}. {gif}")
    print("=" * 60)
    print("✅ База данных готова")
    print("🚀 Запуск ботов...")
    print("=" * 60)
    print("📱 Основной бот: БЕЗ GIF при старте")
    print("🎯 GIF при нажатии на кнопки")
    print("📋 Бот-логгер активен")
    print("=" * 60)
    print("🟢 Боты работают! Нажмите Ctrl+C для остановки")
    print("=" * 60)
    
    await asyncio.gather(
        main_dp.start_polling(main_bot),
        logger_dp.start_polling(logger_bot)
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Боты остановлены пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()