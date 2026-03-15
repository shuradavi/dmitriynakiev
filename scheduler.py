import logging
from datetime import datetime, timedelta
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from database import async_session
from models import Pet, Reminder
from config import REMINDER_CHECK_INTERVAL, DEFAULT_FEEDING_HOURS, DEFAULT_CLEANING_DAYS

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

# Эта функция будет переопределена в bot.py
send_reminder_to_user = None


class ReminderManager:
    """Менеджер напоминаний"""

    @staticmethod
    async def check_feeding_reminders():
        """Проверка напоминаний о кормлении"""
        if not send_reminder_to_user:
            logger.warning("Функция send_reminder_to_user не настроена")
            return

        async with async_session() as session:
            query = select(Pet).where(
                and_(
                    Pet.is_active == True,
                    Pet.last_feeding.isnot(None)
                )
            )
            result = await session.execute(query)
            pets = result.scalars().all()

            current_time = datetime.now()

            for pet in pets:
                if pet.last_feeding:
                    next_feeding = pet.last_feeding + timedelta(hours=pet.feeding_interval_hours)
                    if current_time >= next_feeding:
                        # Создаем напоминание в БД
                        reminder = Reminder(
                            user_id=pet.user_id,
                            pet_id=pet.id,
                            reminder_type="feeding",
                            message=f"Пора покормить {pet.name or pet.species}! "
                                    f"Последнее кормление было: {pet.last_feeding.strftime('%d.%m.%Y в %H:%M')}",
                            scheduled_time=current_time,
                            is_sent=False
                        )
                        session.add(reminder)

                        # Отправляем напоминание пользователю
                        try:
                            await send_reminder_to_user(
                                pet.user_id,
                                f"⏰ Пора покормить {pet.name or pet.species}!\n"
                                f"Последнее кормление было: {pet.last_feeding.strftime('%d.%m.%Y в %H:%M')}"
                            )
                            reminder.is_sent = True
                            reminder.sent_at = current_time
                        except Exception as e:
                            logger.error(f"Ошибка отправки напоминания user_id={pet.user_id}: {e}")

            await session.commit()

    @staticmethod
    async def check_cleaning_reminders():
        """Проверка напоминаний об уборке"""
        if not send_reminder_to_user:
            logger.warning("Функция send_reminder_to_user не настроена")
            return

        async with async_session() as session:
            query = select(Pet).where(
                and_(
                    Pet.is_active == True,
                    Pet.last_cleaning.isnot(None)
                )
            )
            result = await session.execute(query)
            pets = result.scalars().all()

            current_time = datetime.now()

            for pet in pets:
                if pet.last_cleaning:
                    next_cleaning = pet.last_cleaning + timedelta(days=pet.cleaning_interval_days)
                    if current_time >= next_cleaning:
                        # Создаем напоминание в БД
                        reminder = Reminder(
                            user_id=pet.user_id,
                            pet_id=pet.id,
                            reminder_type="cleaning",
                            message=f"Пора убраться у {pet.name or pet.species}! "
                                    f"Последняя уборка была: {pet.last_cleaning.strftime('%d.%m.%Y в %H:%M')}",
                            scheduled_time=current_time,
                            is_sent=False
                        )
                        session.add(reminder)

                        # Отправляем напоминание пользователю
                        try:
                            await send_reminder_to_user(
                                pet.user_id,
                                f"🧹 Пора убраться у {pet.name or pet.species}!\n"
                                f"Последняя уборка была: {pet.last_cleaning.strftime('%d.%m.%Y в %H:%M')}"
                            )
                            reminder.is_sent = True
                            reminder.sent_at = current_time
                        except Exception as e:
                            logger.error(f"Ошибка отправки напоминания user_id={pet.user_id}: {e}")

            await session.commit()


def start_scheduler(bot_instance=None):
    """Запуск планировщика"""
    global send_reminder_to_user

    async def check_and_send_reminders():
        """Проверка и отправка напоминаний"""
        try:
            await ReminderManager.check_feeding_reminders()
            await ReminderManager.check_cleaning_reminders()
            logger.debug("Проверка напоминаний выполнена")
        except Exception as e:
            logger.error(f"Ошибка в check_and_send_reminders: {e}")

    # Настраиваем задачу проверки каждые N минут
    scheduler.add_job(
        check_and_send_reminders,
        IntervalTrigger(minutes=REMINDER_CHECK_INTERVAL),
        id='reminder_check',
        name='Check and send reminders',
        replace_existing=True
    )

    # Запускаем немедленно первую проверку
    scheduler.add_job(
        check_and_send_reminders,
        'date',
        run_date=datetime.now() + timedelta(seconds=30),
        id='initial_check'
    )

    try:
        scheduler.start()
        logger.info(f"✅ Планировщик запущен. Интервал проверки: {REMINDER_CHECK_INTERVAL} минут")
    except Exception as e:
        logger.error(f"❌ Ошибка запуска планировщика: {e}")


def stop_scheduler():
    """Остановка планировщика"""
    try:
        if scheduler.running:
            scheduler.shutdown(wait=False)
            logger.info("Планировщик остановлен")
    except Exception as e:
        logger.error(f"Ошибка остановки планировщика: {e}")