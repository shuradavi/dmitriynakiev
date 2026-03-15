import os
import sys

# Токен напрямую (для тестирования)
BOT_TOKEN = "8541102393:AAGNFCAvcKz7cmzAeFEBPdut-4LK4yd37pc"
ADMIN_ID = 349017530
REMINDER_CHECK_INTERVAL = 30
DEFAULT_FEEDING_HOURS = 8
DEFAULT_CLEANING_DAYS = 3

print("=" * 50)
print("✅ Конфигурация загружена (прямой токен)!")
print(f"🔑 Токен: {BOT_TOKEN[:10]}...")
print(f"👑 Admin ID: {ADMIN_ID}")
print("=" * 50)

# Проверка длины токена
if len(BOT_TOKEN) < 30:
    print("⚠️ Внимание: токен слишком короткий!")
    print("Проверьте, что токен скопирован полностью из @BotFather")