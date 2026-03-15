#!/usr/bin/env python3
"""
Упрощенный запуск бота для ухода за питомцами
"""

import asyncio
import logging
import sys
import os

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Проверка зависимостей
try:
    import aiogram
    import sqlalchemy
    import aiosqlite
    import apscheduler
    import greenlet

    print("✅ Все зависимости установлены")
except ImportError as e:
    print(f"❌ Отсутствует зависимость: {e}")
    print("\nУстановите зависимости командой:")
    print("pip install aiogram sqlalchemy aiosqlite apscheduler greenlet")
    sys.exit(1)

# Токен бота (можно указать прямо здесь)
BOT_TOKEN = "8541102393:AAGNFCAvcKz7cmzAeFEBPdut-4LK4yd37pc"
ADMIN_ID = 349017530

print("=" * 50)
print("🐕‍🦺 Запуск бота для ухода за питомцами")
print(f"🔑 Токен: {BOT_TOKEN[:10]}...")
print(f"👑 Admin ID: {ADMIN_ID}")
print("=" * 50)


async def main():
    """Запуск основного бота"""
    try:
        # Импортируем здесь, чтобы увидеть ошибки импорта
        from aiogram import Bot, Dispatcher
        from aiogram.filters import CommandStart
        from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
        from database import init_db

        # Инициализация бота
        bot = Bot(token=BOT_TOKEN)
        dp = Dispatcher()

        # Инициализация БД
        await init_db()
        print("✅ База данных инициализирована")

        @dp.message(CommandStart())
        async def cmd_start(message: Message):
            """Обработчик команды /start"""
            keyboard = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="🐾 Добавить питомца")],
                    [KeyboardButton(text="📋 Мои питомцы")],
                    [KeyboardButton(text="🍽️ Записать кормление")]
                ],
                resize_keyboard=True
            )

            await message.answer(
                "🐕‍🦺 Добро пожаловать в бот для ухода за питомцами!\n"
                "Выберите действие:",
                reply_markup=keyboard
            )

        @dp.message(lambda message: message.text == "🐾 Добавить питомца")
        async def add_pet(message: Message):
            await message.answer("Функция добавления питомца")

        @dp.message(lambda message: message.text == "📋 Мои питомцы")
        async def show_pets(message: Message):
            await message.answer("Функция показа питомцев")

        @dp.message(lambda message: message.text == "🍽️ Записать кормление")
        async def record_feeding(message: Message):
            await message.answer("Функция записи кормления")

        # Запуск бота
        print("✅ Бот запущен и ожидает сообщений...")
        await dp.start_polling(bot)

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен")