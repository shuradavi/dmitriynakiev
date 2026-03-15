import logging
import asyncio
import sys
import re
import aiogram
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any, Union, List, Callable

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

# Конфигурация
BOT_TOKEN = "8541102393:AAGNFCAvcKz7cmzAeFEBPdut-4LK4yd37pc"
ADMIN_ID = 368069058
from database import init_db, async_session
from models import User, Pet

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log')
    ]
)
logger = logging.getLogger(__name__)

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


# ========== УТИЛИТЫ ==========
class TextTemplates:
    """Шаблоны текстовых сообщений"""
    WELCOME = (
        "🕷️ *Добро пожаловать в бот для ухода за паукообразными и другими членистоногими!*\n\n"
        "*Особенности бота:*\n"
        "• Запись кормления, линьки и уборки\n"
        "• 📈 Подсчет линек вместо возраста\n"
        "• 📊 Статистика и история ухода\n"
        "• 🗑️ Управление списком питомцев\n"
        "• 🗓️ Выбор даты для событий\n\n"
        "НАШ КАНАЛ О ПАУКАХ: https://t.me/toxicnesss\n\n"
    
        "Выберите действие из меню ниже:"
        
    )

    ADMIN_PANEL = (
        "🛠️ *Панель администратора*\n\n"
        "Доступные функции:\n"
        "• 👥 Общая статистика - статистика по всему боту\n"
        "• 📈 Статистика по пользователю - детальная статистика по конкретному пользователю\n"
        "• 📋 Список пользователей - список всех пользователей бота\n"
        "• 📊 Топ активных пользователей - пользователи с наибольшим количеством питомцев\n"
        "• 📅 Активность за период - статистика активности за выбранный период\n"
        "• ⬅️ Назад в меню - вернуться в основное меню"
    )

    HELP = (
        "📖 *Справка по боту:*\n\n"
        "*/start* - Начать работу с ботом\n"
        "*/help* - Показать эту справку\n"
        "*/pets* - Показать всех питомцев\n\n"
        "*Основные функции:*\n"
        "• 🐾 *Добавить питомца* - добавление нового питомца\n"
        "• 📋 *Мои питомцы* - список всех ваших питомцев\n"
        "• 🍽️ *Записать кормление* - запись времени кормления (можно выбрать дату)\n"
        "• 🔄 *Записать линьку* - запись линьки (+1 к количеству линек, можно выбрать дату)\n"
        "• 🧹 *Записать уборку* - запись времени уборки (можно выбрать дату)\n"
        "• 🗑️ *Удалить питомца* - удаление питомца и всех его данных\n"
        "• 📊 *Статистика* - просмотр статистики\n"
        "{admin_section}"
        "\n*Форматы даты:*\n"
        "• `25.12.2023 14:30` - полный формат\n"
        "• `25.12 14:30` - день и месяц (год текущий)\n"
        "• `25.12.2023` - только дата (время 00:00)\n"
        "• `14:30` - только время (дата сегодня)\n"
        "• `сегодня` или `today` - сегодня 00:00\n"
        "• `вчера` или `yesterday` - вчера 00:00\n"
        "• `сегодня 14:30` - сегодня в указанное время\n\n"
        "*Важно:* При каждой записи линьки количество линек увеличивается на 1!\n\n"
        "Бот автоматически сохраняет все данные!"
    )

    DATE_FORMATS = (
        "📝 *Введите дату и время события:*\n\n"
        "*Примеры форматов:*\n"
        "• `25.12.2023 14:30` - полный формат\n"
        "• `25.12 14:30` - день и месяц (год текущий)\n"
        "• `25.12.2023` - только дата (время 00:00)\n"
        "• `14:30` - только время (дата сегодня)\n"
        "• `сегодня` или `today` - сегодня 00:00\n"
        "• `вчера` или `yesterday` - вчера 00:00\n"
        "• `сегодня 14:30` - сегодня в указанное время\n\n"
        "Для отмены введите 'отмена' или нажмите кнопку отмены ниже."
    )


class ValidationUtils:
    """Утилиты для валидации и преобразования данных"""

    @staticmethod
    def increment_molts(age_str: str) -> str:
        """Увеличивает количество линек на 1"""
        if not age_str or not isinstance(age_str, str):
            return "1"

        age_str = age_str.strip()
        molts = 0

        num_match = re.search(r'(\d+)', age_str)
        if num_match:
            try:
                molts = int(num_match.group(1))
            except ValueError:
                molts = 0
        else:
            if "один" in age_str.lower() or "перв" in age_str.lower():
                molts = 1
            elif "два" in age_str.lower() or "втор" in age_str.lower():
                molts = 2
            elif "три" in age_str.lower() or "трет" in age_str.lower():
                molts = 3

        return str(molts + 1)

    @staticmethod
    def format_molts(molts_str: str) -> str:
        """Форматирует количество линек в удобочитаемый вид"""
        try:
            molts = int(molts_str)
            if molts == 1:
                return "1 линька"
            elif 2 <= molts <= 4:
                return f"{molts} линьки"
            else:
                return f"{molts} линек"
        except (ValueError, TypeError):
            return molts_str

    @staticmethod
    def parse_custom_date(date_str: str) -> Optional[datetime]:
        """Парсит дату из строки в различных форматах"""
        if not date_str:
            return None

        date_str = date_str.strip()
        current_year = datetime.now().year

        formats = [
            "%d.%m.%Y %H:%M",
            "%d.%m.%y %H:%M",
            "%d.%m.%Y",
            "%d.%m.%y",
            "%d.%m %H:%M",
            "%d.%m",
            "%H:%M",
            "today %H:%M",
            "yesterday %H:%M",
            "today",
            "yesterday",
        ]

        date_str_lower = date_str.lower()
        if date_str_lower == "сегодня" or date_str_lower == "today":
            return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        elif date_str_lower == "вчера" or date_str_lower == "yesterday":
            return (datetime.now() - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

        for fmt in formats:
            try:
                if fmt in ["%d.%m %H:%M", "%d.%m"]:
                    date_str_with_year = f"{date_str}.{current_year}"
                    fmt_with_year = fmt.replace("%d.%m", "%d.%m.%Y")
                    return datetime.strptime(date_str_with_year, fmt_with_year)
                elif fmt == "%H:%M":
                    now = datetime.now()
                    time_only = datetime.strptime(date_str, "%H:%M")
                    return now.replace(hour=time_only.hour, minute=time_only.minute, second=0, microsecond=0)
                elif fmt in ["today %H:%M", "yesterday %H:%M"]:
                    parts = date_str.split()
                    if len(parts) == 2:
                        day_keyword, time_str = parts[0].lower(), parts[1]
                        time_obj = datetime.strptime(time_str, "%H:%M")
                        base_date = datetime.now() if day_keyword == "today" else datetime.now() - timedelta(days=1)
                        return base_date.replace(hour=time_obj.hour, minute=time_obj.minute, second=0, microsecond=0)
                else:
                    return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        return None

    @staticmethod
    def format_date_for_display(dt: datetime) -> str:
        """Форматирует дату для отображения пользователю"""
        if not dt:
            return "не указано"

        if dt.date() == datetime.now().date():
            return f"сегодня в {dt.strftime('%H:%M')}"
        elif dt.date() == (datetime.now() - timedelta(days=1)).date():
            return f"вчера в {dt.strftime('%H:%M')}"
        else:
            return dt.strftime('%d.%m.%Y %H:%M')


class KeyboardManager:
    """Менеджер клавиатур"""

    @staticmethod
    def get_main_keyboard() -> types.ReplyKeyboardMarkup:
        """Основное меню"""
        buttons = [
            [types.KeyboardButton(text="🐾 Добавить питомца")],
            [types.KeyboardButton(text="📋 Мои питомцы")],
            [types.KeyboardButton(text="🍽️ Записать кормление")],
            [types.KeyboardButton(text="🔄 Записать линьку")],
            [types.KeyboardButton(text="🧹 Записать уборку")],
            [types.KeyboardButton(text="🗑️ Удалить питомца")],
            [types.KeyboardButton(text="📊 Статистика")]
        ]
        return types.ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

    @staticmethod
    def get_admin_keyboard() -> types.ReplyKeyboardMarkup:
        """Клавиатура администратора"""
        buttons = [
            [types.KeyboardButton(text="👥 Общая статистика")],
            [types.KeyboardButton(text="📈 Статистика по пользователю")],
            [types.KeyboardButton(text="📋 Список пользователей")],
            [types.KeyboardButton(text="📊 Топ активных пользователей")],
            [types.KeyboardButton(text="📅 Активность за период")],
            [types.KeyboardButton(text="⬅️ Назад в меню")]
        ]
        return types.ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

    @staticmethod
    def get_cancel_keyboard() -> types.ReplyKeyboardMarkup:
        """Клавиатура для отмены"""
        return types.ReplyKeyboardMarkup(
            keyboard=[[types.KeyboardButton(text="❌ Отмена")]],
            resize_keyboard=True
        )

    @staticmethod
    def get_skip_keyboard() -> types.ReplyKeyboardMarkup:
        """Клавиатура с пропуском"""
        buttons = [
            [types.KeyboardButton(text="⏭️ Пропустить")],
            [types.KeyboardButton(text="❌ Отмена")]
        ]
        return types.ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

    @staticmethod
    def get_date_option_keyboard() -> types.InlineKeyboardMarkup:
        """Клавиатура для выбора варианта даты"""
        builder = InlineKeyboardBuilder()
        builder.button(text="📅 Сейчас", callback_data="date_now")
        builder.button(text="🗓️ Указать другую дату", callback_data="date_custom")
        builder.button(text="❌ Отмена", callback_data="cancel_event")
        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def get_confirmation_keyboard() -> types.InlineKeyboardMarkup:
        """Клавиатура для подтверждения события"""
        builder = InlineKeyboardBuilder()
        builder.button(text="✅ Подтвердить", callback_data="confirm_event")
        builder.button(text="✏️ Изменить дату", callback_data="change_date")
        builder.button(text="❌ Отмена", callback_data="cancel_event")
        builder.adjust(1)
        return builder.as_markup()

    @staticmethod
    def get_pets_selection_keyboard(pets: List[Pet], action_prefix: str = "select") -> types.InlineKeyboardMarkup:
        """Клавиатура для выбора питомца"""
        builder = InlineKeyboardBuilder()
        for pet in pets:
            display_name = pet.name or pet.species
            if len(display_name) > 15:
                display_name = display_name[:13] + ".."
            builder.button(
                text=display_name,
                callback_data=f"pet_{action_prefix}_{pet.id}"
            )
        builder.button(text="❌ Отмена", callback_data=f"cancel_{action_prefix}")
        builder.adjust(1)
        return builder.as_markup()


class DatabaseManager:
    """Менеджер работы с базой данных"""

    @staticmethod
    async def ensure_user_in_db(user_id: int, **user_data) -> User:
        """Гарантирует, что пользователь есть в базе данных"""
        async with async_session() as session:
            user = await session.get(User, user_id)
            if not user:
                user = User(
                    id=user_id,
                    username=user_data.get('username'),
                    first_name=user_data.get('first_name'),
                    last_name=user_data.get('last_name'),
                    language_code=user_data.get('language_code'),
                    last_active=datetime.now()
                )
                session.add(user)
                await session.commit()
                logger.info(f"Пользователь {user_id} добавлен в базу данных")
                return user
            else:
                user.last_active = datetime.now()
                await session.commit()
                return user

    @staticmethod
    async def get_user_pets(user_id: int) -> List[Pet]:
        """Получает всех питомцев пользователя"""
        async with async_session() as session:
            query = select(Pet).where(Pet.user_id == user_id)
            result = await session.execute(query)
            return result.scalars().all()

    @staticmethod
    async def get_pet_by_id(pet_id: int, user_id: Optional[int] = None) -> Optional[Pet]:
        """Получает питомца по ID с опциональной проверкой владельца"""
        async with async_session() as session:
            pet = await session.get(Pet, pet_id)
            if pet and (user_id is None or pet.user_id == user_id):
                return pet
            return None

    @staticmethod
    async def save_pet(pet_data: Dict[str, Any], user_id: int) -> Pet:
        """Сохраняет нового питомца"""
        async with async_session() as session:
            pet = Pet(
                user_id=user_id,
                species=pet_data['species'],
                name=pet_data.get('name'),
                age=pet_data.get('age', '0'),
                feeding_interval_hours=8,
                cleaning_interval_days=3,
                is_active=True
            )
            session.add(pet)
            await session.commit()
            return pet

    @staticmethod
    async def delete_pet(pet_id: int, user_id: int) -> bool:
        """Удаляет питомца с проверкой владельца"""
        async with async_session() as session:
            pet = await session.get(Pet, pet_id)
            if not pet or pet.user_id != user_id:
                return False

            await session.delete(pet)
            await session.commit()
            return True

    @staticmethod
    async def record_event(pet_id: int, event_type: str, event_datetime: datetime, user_id: int) -> Tuple[bool, str]:
        """Записывает событие для питомца"""
        try:
            async with async_session() as session:
                pet = await session.get(Pet, pet_id)

                if not pet:
                    return False, "Питомец не найден"

                if pet.user_id != user_id:
                    return False, "Нет прав для записи события"

                if event_datetime > datetime.now():
                    return False, "Дата события не может быть в будущем"

                old_molts = pet.age
                new_molts = None

                if event_type == "feeding":
                    pet.last_feeding = event_datetime
                elif event_type == "molt":
                    pet.last_molt = event_datetime
                    if pet.age:
                        pet.age = ValidationUtils.increment_molts(pet.age)
                        new_molts = pet.age
                        logger.info(f"Количество линек питомца {pet.id} обновлено: {old_molts} -> {pet.age}")
                elif event_type == "cleaning":
                    pet.last_cleaning = event_datetime

                pet.updated_at = datetime.now()

                user = await session.get(User, user_id)
                if user:
                    user.last_active = datetime.now()

                await session.commit()

                logger.info(f"Записано {event_type} для питомца {pet_id} на {event_datetime}")
                return True, new_molts or old_molts or "0"

        except Exception as e:
            logger.error(f"Ошибка записи события: {e}")
            return False, f"Ошибка: {str(e)}"


class AdminManager:
    """Менеджер административных функций"""

    @staticmethod
    async def is_admin(user_id: int) -> bool:
        """Проверяет, является ли пользователь администратором"""
        return user_id == ADMIN_ID

    @staticmethod
    async def get_admin_stats() -> Dict[str, Any]:
        """Получает общую статистику по боту"""
        async with async_session() as session:
            stats = {}

            # Статистика пользователей
            total_users_query = select(func.count(User.id))
            stats['total_users'] = (await session.execute(total_users_query)).scalar() or 0

            month_ago = datetime.now() - timedelta(days=30)
            new_users_query = select(func.count(User.id)).where(User.created_at >= month_ago)
            stats['new_users'] = (await session.execute(new_users_query)).scalar() or 0

            # Статистика питомцев
            total_pets_query = select(func.count(Pet.id))
            stats['total_pets'] = (await session.execute(total_pets_query)).scalar() or 0

            active_pets_query = select(func.count(Pet.id)).where(
                (Pet.last_feeding.is_not(None)) |
                (Pet.last_molt.is_not(None)) |
                (Pet.last_cleaning.is_not(None))
            )
            stats['active_pets'] = (await session.execute(active_pets_query)).scalar() or 0

            # Статистика событий
            feeding_count_query = select(func.count(Pet.id)).where(Pet.last_feeding.is_not(None))
            stats['feeding_count'] = (await session.execute(feeding_count_query)).scalar() or 0

            molt_count_query = select(func.count(Pet.id)).where(Pet.last_molt.is_not(None))
            stats['molt_count'] = (await session.execute(molt_count_query)).scalar() or 0

            cleaning_count_query = select(func.count(Pet.id)).where(Pet.last_cleaning.is_not(None))
            stats['cleaning_count'] = (await session.execute(cleaning_count_query)).scalar() or 0

            # Общее количество линек
            pets_query = select(Pet)
            pets_result = await session.execute(pets_query)
            pets = pets_result.scalars().all()

            stats['total_molts'] = 0
            for pet in pets:
                try:
                    molts_match = re.search(r'(\d+)', pet.age)
                    if molts_match:
                        stats['total_molts'] += int(molts_match.group(1))
                except:
                    pass

            # Активность за последние 7 дней
            week_ago = datetime.now() - timedelta(days=7)
            recent_activity_query = select(func.count(Pet.id)).where(Pet.updated_at >= week_ago)
            stats['recent_activity'] = (await session.execute(recent_activity_query)).scalar() or 0

            # Самые популярные виды
            species_query = select(Pet.species, func.count(Pet.id).label('count')).group_by(Pet.species).order_by(
                desc('count')).limit(10)
            species_result = await session.execute(species_query)
            stats['top_species'] = species_result.all()

            # Среднее количество питомцев на пользователя
            stats['avg_pets_per_user'] = 0
            if stats['total_users'] > 0:
                stats['avg_pets_per_user'] = round(stats['total_pets'] / stats['total_users'], 1)

            return stats

    @staticmethod
    async def get_user_stats(user_id: int) -> Optional[Dict[str, Any]]:
        """Получает статистику по конкретному пользователю"""
        async with async_session() as session:
            user = await session.get(User, user_id)
            if not user:
                return None

            pets = await DatabaseManager.get_user_pets(user_id)
            pets_count = len(pets)

            # Статистика
            total_molts = 0
            for pet in pets:
                try:
                    molts_match = re.search(r'(\d+)', pet.age)
                    if molts_match:
                        total_molts += int(molts_match.group(1))
                except:
                    pass

            # Популярные виды у пользователя
            if pets:
                user_species = {}
                for pet in pets:
                    user_species[pet.species] = user_species.get(pet.species, 0) + 1
                top_user_species = sorted(user_species.items(), key=lambda x: x[1], reverse=True)[:5]
            else:
                top_user_species = []

            # Дата первого питомца
            first_pet_date = None
            if pets:
                first_pet_date = min(pet.created_at for pet in pets)

            return {
                'user': user,
                'pets_count': pets_count,
                'total_molts': total_molts,
                'feeding_count': sum(1 for p in pets if p.last_feeding),
                'molt_count': sum(1 for p in pets if p.last_molt),
                'cleaning_count': sum(1 for p in pets if p.last_cleaning),
                'last_active': user.last_active or user.created_at,
                'top_species': top_user_species,
                'first_pet_date': first_pet_date,
                'pets': pets[:10]
            }

    @staticmethod
    async def get_users_list(limit: int = 50) -> List[User]:
        """Получает список пользователей"""
        async with async_session() as session:
            query = select(User).order_by(desc(User.created_at)).limit(limit)
            result = await session.execute(query)
            return result.scalars().all()

    @staticmethod
    async def get_top_active_users(limit: int = 10) -> List[Tuple[User, int]]:
        """Получает топ активных пользователей по количеству питомцев"""
        async with async_session() as session:
            subquery = select(Pet.user_id, func.count(Pet.id).label('pet_count')).group_by(Pet.user_id).subquery()
            query = select(User, subquery.c.pet_count).join(
                subquery, User.id == subquery.c.user_id, isouter=True
            ).order_by(desc(subquery.c.pet_count)).limit(limit)
            result = await session.execute(query)
            return result.all()


# ========== СОСТОЯНИЯ ==========
class AddPetStates(StatesGroup):
    waiting_for_species = State()
    waiting_for_name = State()
    waiting_for_molts = State()


class DeletePetStates(StatesGroup):
    choosing_pet = State()
    confirming = State()


class EventStates(StatesGroup):
    """Состояния для записи событий с выбором даты"""
    choosing_pet = State()
    choosing_date_option = State()
    entering_custom_date = State()
    confirming_event = State()


class AdminStates(StatesGroup):
    """Состояния для администратора"""
    waiting_for_user_id = State()


# ========== ОСНОВНЫЕ ОБРАБОТЧИКИ ==========
@dp.message(CommandStart())
async def cmd_start(message: Message):
    """Обработчик /start"""
    await DatabaseManager.ensure_user_in_db(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        language_code=message.from_user.language_code
    )

    await message.answer(
        TextTemplates.WELCOME,
        reply_markup=KeyboardManager.get_main_keyboard(),
        parse_mode="Markdown"
    )


@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    """Команда администратора"""
    user_id = message.from_user.id

    if not await AdminManager.is_admin(user_id):
        await message.answer("❌ У вас нет прав доступа к этой команде.")
        return

    await DatabaseManager.ensure_user_in_db(
        user_id=user_id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        language_code=message.from_user.language_code
    )

    await message.answer(
        TextTemplates.ADMIN_PANEL,
        reply_markup=KeyboardManager.get_admin_keyboard(),
        parse_mode="Markdown"
    )


@dp.message(F.text == "👥 Общая статистика")
async def admin_general_stats(message: Message):
    """Общая статистика для администратора"""
    if not await AdminManager.is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав доступа.")
        return

    await message.answer("📊 *Сбор статистики...*", parse_mode="Markdown")

    try:
        stats = await AdminManager.get_admin_stats()

        report = "📈 *ОБЩАЯ СТАТИСТИКА БОТА*\n\n"
        report += "👥 *ПОЛЬЗОВАТЕЛИ:*\n"
        report += f"• Всего пользователей: {stats['total_users']}\n"
        report += f"• Новых за 30 дней: {stats['new_users']}\n"
        report += f"• Среднее питомцев на пользователя: {stats['avg_pets_per_user']}\n\n"

        report += "🕷️ *ПИТОМЦЫ:*\n"
        report += f"• Всего питомцев: {stats['total_pets']}\n"
        report += f"• Активных питомцев: {stats['active_pets']}\n"
        report += f"• Всего линек: {stats['total_molts']}\n\n"

        report += "📊 *СОБЫТИЯ:*\n"
        report += f"• Кормлений: {stats['feeding_count']}\n"
        report += f"• Линек: {stats['molt_count']}\n"
        report += f"• Уборок: {stats['cleaning_count']}\n"
        report += f"• Активных за 7 дней: {stats['recent_activity']}\n\n"

        if stats['top_species']:
            report += "🏆 *ТОП ВИДОВ ПИТОМЦЕВ:*\n"
            for i, (species, count) in enumerate(stats['top_species'], 1):
                report += f"{i}. {species}: {count}\n"

        await message.answer(report, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        await message.answer("❌ Ошибка при получении статистики.")


@dp.message(F.text == "📈 Статистика по пользователю")
async def admin_user_stats_start(message: Message, state: FSMContext):
    """Начало получения статистики по пользователю"""
    if not await AdminManager.is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав доступа.")
        return

    await state.set_state(AdminStates.waiting_for_user_id)
    await message.answer(
        "Введите ID пользователя или его @username:\n\n"
        "*Примеры:*\n"
        "• `123456789` - ID пользователя\n"
        "• `@username` - имя пользователя\n\n"
        "Для отмены введите 'отмена'",
        reply_markup=KeyboardManager.get_cancel_keyboard(),
        parse_mode="Markdown"
    )


@dp.message(AdminStates.waiting_for_user_id)
async def admin_user_stats_process(message: Message, state: FSMContext):
    """Обработка запроса статистики по пользователю"""
    if message.text == "❌ Отмена" or message.text.lower() == "отмена":
        await state.clear()
        await message.answer("❌ Отменено.", reply_markup=KeyboardManager.get_admin_keyboard())
        return

    user_input = message.text.strip()

    try:
        async with async_session() as session:
            user = None

            if user_input.isdigit():
                user_id = int(user_input)
                user = await session.get(User, user_id)
            elif user_input.startswith('@'):
                username = user_input[1:]
                query = select(User).where(User.username == username)
                result = await session.execute(query)
                user = result.scalar_one_or_none()
            else:
                query = select(User).where(User.username == user_input)
                result = await session.execute(query)
                user = result.scalar_one_or_none()

            if not user:
                await message.answer("❌ Пользователь не найден.")
                return

            stats = await AdminManager.get_user_stats(user.id)

            if not stats:
                await message.answer("❌ Не удалось получить статистику.")
                return

            report = f"📊 *СТАТИСТИКА ПОЛЬЗОВАТЕЛЯ*\n\n"
            report += f"👤 *ИНФОРМАЦИЯ:*\n"
            report += f"• ID: {user.id}\n"
            report += f"• Имя: {user.first_name or 'Не указано'}\n"

            if user.last_name:
                report += f"• Фамилия: {user.last_name}\n"
            if user.username:
                report += f"• Username: @{user.username}\n"

            report += f"• Язык: {user.language_code or 'Не указан'}\n"
            report += f"• Зарегистрирован: {user.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            report += f"• Последняя активность: {stats['last_active'].strftime('%d.%m.%Y %H:%M')}\n\n"

            report += f"🕷️ *СТАТИСТИКА:*\n"
            report += f"• Питомцев: {stats['pets_count']}\n"
            report += f"• Всего линек: {stats['total_molts']}\n"
            report += f"• Кормлений: {stats['feeding_count']}\n"
            report += f"• Линек: {stats['molt_count']}\n"
            report += f"• Уборок: {stats['cleaning_count']}\n"

            if stats['first_pet_date']:
                report += f"• Первый питомец: {stats['first_pet_date'].strftime('%d.%m.%Y')}\n"

            report += "\n"

            if stats['top_species']:
                report += "📋 *ПОПУЛЯРНЫЕ ВИДЫ:*\n"
                for species, count in stats['top_species']:
                    report += f"• {species}: {count}\n"
                report += "\n"

            if stats['pets']:
                report += "📝 *ПИТОМЦЫ:*\n"
                for i, pet in enumerate(stats['pets'], 1):
                    pet_info = f"{i}. {pet.name or 'Без имени'} ({pet.species}) - {ValidationUtils.format_molts(pet.age)}"

                    if pet.last_feeding:
                        pet_info += f"\n   🍽️: {ValidationUtils.format_date_for_display(pet.last_feeding)}"
                    if pet.last_molt:
                        pet_info += f"\n   🔄: {ValidationUtils.format_date_for_display(pet.last_molt)}"
                    if pet.last_cleaning:
                        pet_info += f"\n   🧹: {ValidationUtils.format_date_for_display(pet.last_cleaning)}"

                    report += pet_info + "\n\n"

                if len(stats['pets']) < stats['pets_count']:
                    report += f"... и еще {stats['pets_count'] - len(stats['pets'])} питомцев\n"

            await message.answer(report, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Ошибка получения статистики пользователя: {e}")
        await message.answer("❌ Ошибка при получении статистики.")

    await state.clear()


@dp.message(F.text == "📋 Список пользователей")
async def admin_users_list(message: Message):
    """Список пользователей для администратора"""
    if not await AdminManager.is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав доступа.")
        return

    await message.answer("📋 *Загружаю список пользователей...*", parse_mode="Markdown")

    try:
        users = await AdminManager.get_users_list(limit=50)

        if not users:
            await message.answer("❌ Пользователей не найдено.")
            return

        report = "📋 *СПИСОК ПОЛЬЗОВАТЕЛЕЙ*\n\n"

        for i, user in enumerate(users, 1):
            user_info = f"{i}. "
            if user.first_name:
                user_info += f"{user.first_name}"
                if user.last_name:
                    user_info += f" {user.last_name}"
            else:
                user_info += "Без имени"

            if user.username:
                user_info += f" (@{user.username})"

            user_info += f"\n   ID: {user.id}"
            user_info += f"\n   Дата регистрации: {user.created_at.strftime('%d.%m.%Y')}"

            # Получаем количество питомцев
            pets = await DatabaseManager.get_user_pets(user.id)
            user_info += f"\n   Питомцев: {len(pets)}\n\n"

            # Разбиваем на части, если сообщение слишком длинное
            if len(report + user_info) > 4000:
                await message.answer(report, parse_mode="Markdown")
                report = user_info
            else:
                report += user_info

        if report:
            await message.answer(report, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Ошибка получения списка пользователей: {e}")
        await message.answer("❌ Ошибка при получении списка пользователей.")


@dp.message(F.text == "📊 Топ активных пользователей")
async def admin_top_users(message: Message):
    """Топ активных пользователей"""
    if not await AdminManager.is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав доступа.")
        return

    await message.answer("🏆 *Загружаю топ активных пользователей...*", parse_mode="Markdown")

    try:
        top_users = await AdminManager.get_top_active_users(limit=15)

        if not top_users:
            await message.answer("❌ Данных не найдено.")
            return

        report = "🏆 *ТОП АКТИВНЫХ ПОЛЬЗОВАТЕЛЕЙ*\n\n"
        report += "📊 *По количеству питомцев:*\n\n"

        for i, (user, pet_count) in enumerate(top_users, 1):
            user_info = f"{i}. "
            if user.first_name:
                user_info += f"{user.first_name}"
                if user.last_name:
                    user_info += f" {user.last_name}"
            else:
                user_info += "Без имени"

            if user.username:
                user_info += f" (@{user.username})"

            user_info += f"\n   ID: {user.id}"
            user_info += f"\n   Питомцев: {pet_count or 0}"
            user_info += f"\n   Зарегистрирован: {user.created_at.strftime('%d.%m.%Y')}\n\n"

            report += user_info

        await message.answer(report, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Ошибка получения топа пользователей: {e}")
        await message.answer("❌ Ошибка при получении топа пользователей.")


@dp.message(F.text == "📅 Активность за период")
async def admin_activity_period(message: Message):
    """Активность за период"""
    if not await AdminManager.is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав доступа.")
        return

    # Для простоты возьмем последние 7 дней
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)

    await message.answer("📅 *Анализирую активность за последние 7 дней...*", parse_mode="Markdown")

    try:
        async with async_session() as session:
            # Новые пользователи за период
            new_users_query = select(func.count(User.id)).where(User.created_at.between(start_date, end_date))
            new_users = (await session.execute(new_users_query)).scalar() or 0

            # Новые питомцы за период
            new_pets_query = select(func.count(Pet.id)).where(Pet.created_at.between(start_date, end_date))
            new_pets = (await session.execute(new_pets_query)).scalar() or 0

            # События за период
            feeding_query = select(func.count(Pet.id)).where(Pet.last_feeding.between(start_date, end_date))
            feeding_count = (await session.execute(feeding_query)).scalar() or 0

            molt_query = select(func.count(Pet.id)).where(Pet.last_molt.between(start_date, end_date))
            molt_count = (await session.execute(molt_query)).scalar() or 0

            cleaning_query = select(func.count(Pet.id)).where(Pet.last_cleaning.between(start_date, end_date))
            cleaning_count = (await session.execute(cleaning_query)).scalar() or 0

            # Активные пользователи за период
            active_users_query = select(func.count(func.distinct(Pet.user_id))).where(
                (Pet.last_feeding.between(start_date, end_date)) |
                (Pet.last_molt.between(start_date, end_date)) |
                (Pet.last_cleaning.between(start_date, end_date))
            )
            active_users = (await session.execute(active_users_query)).scalar() or 0

            report = "📅 *АКТИВНОСТЬ ЗА ПЕРИОД*\n\n"
            report += f"*Период:* {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}\n\n"

            report += "👥 *ПОЛЬЗОВАТЕЛИ:*\n"
            report += f"• Новых пользователей: {new_users}\n"
            report += f"• Активных пользователей: {active_users}\n\n"

            report += "🕷️ *ПИТОМЦЫ:*\n"
            report += f"• Новых питомцев: {new_pets}\n\n"

            report += "📊 *СОБЫТИЯ:*\n"
            report += f"• Кормлений: {feeding_count}\n"
            report += f"• Линек: {molt_count}\n"
            report += f"• Уборок: {cleaning_count}\n\n"

            total_events = feeding_count + molt_count + cleaning_count
            report += f"📈 *ВСЕГО СОБЫТИЙ:* {total_events}"

            await message.answer(report, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Ошибка получения активности: {e}")
        await message.answer("❌ Ошибка при получении статистики активности.")


@dp.message(F.text == "⬅️ Назад в меню")
async def admin_back_to_menu(message: Message):
    """Возврат в основное меню из админки"""
    if not await AdminManager.is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав доступа.")
        return

    await message.answer("Возвращаюсь в основное меню...", reply_markup=KeyboardManager.get_main_keyboard())


@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Справка по командам"""
    admin_section = ""

    if await AdminManager.is_admin(message.from_user.id):
        admin_section = (
            "\n\n*Для администратора:*\n"
            "• /admin - Панель администратора\n"
            "• 👥 Общая статистика - статистика по всему боту\n"
            "• 📈 Статистика по пользователю - детальная статистика\n"
            "• 📋 Список пользователей - список всех пользователей\n"
            "• 📊 Топ активных пользователей - пользователи с наибольшим количеством питомцев\n"
            "• 📅 Активность за период - статистика активности\n"
        )

    help_text = TextTemplates.HELP.format(admin_section=admin_section)
    await message.answer(help_text, parse_mode="Markdown")


@dp.message(Command("pets"))
async def cmd_pets(message: Message):
    """Быстрая команда для показа питомцев"""
    await DatabaseManager.ensure_user_in_db(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        language_code=message.from_user.language_code
    )

    pets = await DatabaseManager.get_user_pets(message.from_user.id)

    if not pets:
        await message.answer("У вас нет питомцев.", reply_markup=KeyboardManager.get_main_keyboard())
        return

    response = ["*Ваши питомцы:*"]
    for pet in pets:
        pet_info = f"\n*{pet.name or pet.species}* ({pet.species})"
        pet_info += f"\nЛинек: {ValidationUtils.format_molts(pet.age)}"
        if pet.last_feeding:
            pet_info += f"\n🍽️ Кормление: {ValidationUtils.format_date_for_display(pet.last_feeding)}"
        if pet.last_molt:
            pet_info += f"\n🔄 Линька: {ValidationUtils.format_date_for_display(pet.last_molt)}"
        if pet.last_cleaning:
            pet_info += f"\n🧹 Уборка: {ValidationUtils.format_date_for_display(pet.last_cleaning)}"
        response.append(pet_info)

    await message.answer("\n".join(response), parse_mode="Markdown")


# ========== ДОБАВЛЕНИЕ ПИТОМЦА ==========
@dp.message(F.text == "🐾 Добавить питомца")
async def add_pet_start(message: Message, state: FSMContext):
    """Начало добавления питомца"""
    await DatabaseManager.ensure_user_in_db(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        language_code=message.from_user.language_code
    )

    await state.set_state(AddPetStates.waiting_for_species)
    await message.answer(
        "Введите *вид* вашего питомца:\n"
        "(Например: паук, скорпион, фрин, телифон)",
        reply_markup=KeyboardManager.get_cancel_keyboard(),
        parse_mode="Markdown"
    )


@dp.message(AddPetStates.waiting_for_species)
async def process_species(message: Message, state: FSMContext):
    """Обработка вида питомца"""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Действие отменено.", reply_markup=KeyboardManager.get_main_keyboard())
        return

    await state.update_data(species=message.text.strip())
    await state.set_state(AddPetStates.waiting_for_name)

    await message.answer(
        "Введите *кличку* питомца:\n"
        "(или нажмите '⏭️ Пропустить', если клички нет)",
        reply_markup=KeyboardManager.get_skip_keyboard(),
        parse_mode="Markdown"
    )


@dp.message(AddPetStates.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    """Обработка клички"""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Действие отменено.", reply_markup=KeyboardManager.get_main_keyboard())
        return

    pet_name = None if message.text == "⏭️ Пропустить" else message.text.strip()
    await state.update_data(name=pet_name)
    await state.set_state(AddPetStates.waiting_for_molts)

    await message.answer(
        "Введите *количество линек* питомца:\n"
        "(Например: 1, 6, 3)\n"
        "Можно ввести просто число или с указанием 'линек'",
        reply_markup=KeyboardManager.get_cancel_keyboard(),
        parse_mode="Markdown"
    )


@dp.message(AddPetStates.waiting_for_molts)
async def process_molts(message: Message, state: FSMContext):
    """Обработка количества линек и сохранение"""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Действие отменено.", reply_markup=KeyboardManager.get_main_keyboard())
        return

    user_data = await state.get_data()

    try:
        # Форматируем количество линек
        molts_text = message.text.strip()
        molts_match = re.search(r'(\d+)', molts_text)
        molts = molts_match.group(1) if molts_match else "0"

        user_data['age'] = molts
        pet = await DatabaseManager.save_pet(user_data, message.from_user.id)

        await state.clear()

        response_text = (
            "✅ *Питомец успешно добавлен!*\n\n"
            f"*Вид:* {pet.species}\n"
            f"*Кличка:* {pet.name or 'не указана'}\n"
            f"*Линек:* {ValidationUtils.format_molts(pet.age)}\n\n"
            "Теперь вы можете записывать кормление, линьку и уборку!"
        )

        await message.answer(
            response_text,
            reply_markup=KeyboardManager.get_main_keyboard(),
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Ошибка добавления питомца: {e}")
        await message.answer(
            "❌ Произошла ошибка при добавлении питомца.",
            reply_markup=KeyboardManager.get_main_keyboard()
        )


# ========== ПОКАЗ ПИТОМЦЕВ ==========
@dp.message(F.text == "📋 Мои питомцы")
async def show_pets(message: Message):
    """Показать всех питомцев"""
    await DatabaseManager.ensure_user_in_db(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        language_code=message.from_user.language_code
    )

    pets = await DatabaseManager.get_user_pets(message.from_user.id)

    if not pets:
        await message.answer(
            "🕷️ У вас пока нет добавленных питомцев.\n"
            "Добавьте первого питомца через меню!",
            reply_markup=KeyboardManager.get_main_keyboard()
        )
        return

    response_parts = ["📋 *Ваши питомцы:*"]
    for idx, pet in enumerate(pets, 1):
        pet_info = [
            f"\n{idx}. *{pet.name or pet.species}* ({pet.species})",
            f"   Линек: {ValidationUtils.format_molts(pet.age)}",
            f"   Добавлен: {pet.created_at.strftime('%d.%m.%Y')}"
        ]

        if pet.last_feeding:
            pet_info.append(f"   🍽️ Кормление: {ValidationUtils.format_date_for_display(pet.last_feeding)}")
        else:
            pet_info.append("   🍽️ Кормление: еще не было")

        if pet.last_cleaning:
            pet_info.append(f"   🧹 Уборка: {ValidationUtils.format_date_for_display(pet.last_cleaning)}")
        else:
            pet_info.append("   🧹 Уборка: еще не было")

        if pet.last_molt:
            pet_info.append(f"   🔄 Линька: {ValidationUtils.format_date_for_display(pet.last_molt)}")
        else:
            pet_info.append("   🔄 Линька: еще не было")

        response_parts.append("\n".join(pet_info))

    response = "\n".join(response_parts)
    await message.answer(response, parse_mode="Markdown")


# ========== ЗАПИСЬ СОБЫТИЙ С ВЫБОРОМ ДАТЫ ==========
@dp.message(F.text == "🍽️ Записать кормление")
async def start_feeding(message: Message, state: FSMContext):
    """Начало записи кормления"""
    await start_event(message, state, "feeding", "кормление")


@dp.message(F.text == "🔄 Записать линьку")
async def start_molt(message: Message, state: FSMContext):
    """Начало записи линьки"""
    await start_event(message, state, "molt", "линьку")


@dp.message(F.text == "🧹 Записать уборку")
async def start_cleaning(message: Message, state: FSMContext):
    """Начало записи уборки"""
    await start_event(message, state, "cleaning", "уборку")


async def start_event(message: Message, state: FSMContext, event_type: str, event_name: str):
    """Общая функция начала записи события"""
    await DatabaseManager.ensure_user_in_db(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        language_code=message.from_user.language_code
    )

    await select_pet_for_event_with_date(message, state, event_type, event_name)


async def select_pet_for_event_with_date(message: Message, state: FSMContext, event_type: str, event_name: str):
    """Выбор питомца для записи события с датой"""
    pets = await DatabaseManager.get_user_pets(message.from_user.id)

    if not pets:
        await message.answer("У вас нет питомцев.", reply_markup=KeyboardManager.get_main_keyboard())
        return

    await state.update_data(event_type=event_type, event_name=event_name)

    if len(pets) == 1:
        # Если один питомец - сразу переходим к выбору даты
        pet = pets[0]
        await state.update_data(pet_id=pet.id, pet_name=pet.name or pet.species)
        # Устанавливаем состояние выбора даты
        await state.set_state(EventStates.choosing_date_option)
        # Отправляем сообщение с выбором даты
        await ask_date_option(message, state)
    else:
        # Если несколько питомцев - показываем выбор
        await state.set_state(EventStates.choosing_pet)

        event_icons = {
            "feeding": "🍽️",
            "molt": "🔄",
            "cleaning": "🧹"
        }
        icon = event_icons.get(event_type, "📝")

        await message.answer(
            f"{icon} Выберите питомца для записи {event_name}:",
            reply_markup=KeyboardManager.get_pets_selection_keyboard(pets, "select")
        )


@dp.callback_query(EventStates.choosing_pet, F.data.startswith("pet_select_"))
async def process_pet_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора питомца"""
    pet_id = int(callback.data.split("_")[2])

    pet = await DatabaseManager.get_pet_by_id(pet_id, callback.from_user.id)

    if not pet:
        await callback.answer("❌ Питомец не найден.")
        return

    await state.update_data(pet_id=pet.id, pet_name=pet.name or pet.species)
    await state.set_state(EventStates.choosing_date_option)

    # Редактируем существующее сообщение
    await ask_date_option(callback.message, state)
    await callback.answer()


async def ask_date_option(message: Union[Message, types.Message], state: FSMContext):
    """Спросить вариант выбора даты"""
    user_data = await state.get_data()
    event_name = user_data.get('event_name', 'события')
    pet_name = user_data.get('pet_name', 'питомца')

    event_icons = {
        "feeding": "🍽️",
        "molt": "🔄",
        "cleaning": "🧹"
    }
    event_type = user_data.get('event_type')
    icon = event_icons.get(event_type, "📝")

    text = (
        f"{icon} *{event_name.capitalize()} для {pet_name}*\n\n"
        "Выберите вариант даты:\n"
        "• *Сейчас* - записать с текущим временем\n"
        "• *Указать другую дату* - выбрать дату вручную"
    )

    if isinstance(message, Message):
        await message.answer(text, reply_markup=KeyboardManager.get_date_option_keyboard(), parse_mode="Markdown")
    else:
        await message.edit_text(text, reply_markup=KeyboardManager.get_date_option_keyboard(), parse_mode="Markdown")


@dp.callback_query(EventStates.choosing_date_option, F.data == "date_now")
async def process_date_now(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора 'Сейчас'"""
    user_data = await state.get_data()
    event_datetime = datetime.now()

    await state.update_data(event_datetime=event_datetime)
    await confirm_event(callback.message, state)
    await callback.answer()


@dp.callback_query(EventStates.choosing_date_option, F.data == "date_custom")
async def process_date_custom(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора 'Указать другую дату'"""
    await state.set_state(EventStates.entering_custom_date)

    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="cancel_event")

    await callback.message.edit_text(
        TextTemplates.DATE_FORMATS,
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.message(EventStates.entering_custom_date)
async def process_custom_date_input(message: Message, state: FSMContext):
    """Обработка ввода пользовательской даты"""
    if message.text.lower() in ["отмена", "cancel"]:
        await cancel_event_process(message, state)
        return

    date_str = message.text.strip()
    event_datetime = ValidationUtils.parse_custom_date(date_str)

    if not event_datetime:
        await message.answer(
            "❌ Не удалось распознать дату. Пожалуйста, введите дату в одном из поддерживаемых форматов.\n"
            "Пример: `25.12.2023 14:30` или `сегодня 18:00`",
            parse_mode="Markdown"
        )
        return

    # Проверяем, что дата не в будущем
    if event_datetime > datetime.now():
        await message.answer(
            "❌ Дата события не может быть в будущем. Пожалуйста, введите корректную дату."
        )
        return

    await state.update_data(event_datetime=event_datetime)
    await confirm_event(message, state)


async def confirm_event(message: Union[Message, types.Message], state: FSMContext):
    """Показать подтверждение события"""
    user_data = await state.get_data()
    event_type = user_data.get('event_type')
    event_name = user_data.get('event_name')
    pet_name = user_data.get('pet_name')
    event_datetime = user_data.get('event_datetime')

    event_icons = {
        "feeding": "🍽️",
        "molt": "🔄",
        "cleaning": "🧹"
    }
    icon = event_icons.get(event_type, "📝")

    text = (
        f"{icon} *Подтвердите запись {event_name}*\n\n"
        f"*Питомец:* {pet_name}\n"
        f"*Дата и время:* {ValidationUtils.format_date_for_display(event_datetime)}\n\n"
        "✅ *Подтвердить* - записать событие\n"
        "✏️ *Изменить дату* - выбрать другую дату\n"
        "❌ *Отмена* - отменить запись"
    )

    if isinstance(message, Message):
        await message.answer(text, reply_markup=KeyboardManager.get_confirmation_keyboard(), parse_mode="Markdown")
    else:
        await message.edit_text(text, reply_markup=KeyboardManager.get_confirmation_keyboard(), parse_mode="Markdown")

    await state.set_state(EventStates.confirming_event)


@dp.callback_query(EventStates.confirming_event, F.data == "confirm_event")
async def process_event_confirmation(callback: CallbackQuery, state: FSMContext):
    """Обработка подтверждения события"""
    user_data = await state.get_data()

    pet_id = user_data.get('pet_id')
    event_type = user_data.get('event_type')
    event_name = user_data.get('event_name')
    pet_name = user_data.get('pet_name')
    event_datetime = user_data.get('event_datetime')

    if not all([pet_id, event_type, event_datetime]):
        await callback.answer("❌ Недостаточно данных для записи")
        return

    success, result_msg = await DatabaseManager.record_event(
        pet_id,
        event_type,
        event_datetime,
        callback.from_user.id
    )

    if success:
        event_icons = {
            "feeding": "🍽️",
            "molt": "🔄",
            "cleaning": "🧹"
        }
        icon = event_icons.get(event_type, "📝")

        response = f"{icon} *{event_name.capitalize()} записано!*\n\n"
        response += f"*Питомец:* {pet_name}\n"
        response += f"*Дата и время:* {ValidationUtils.format_date_for_display(event_datetime)}"

        # Добавляем информацию о новом количестве линек для линьки
        if event_type == "molt":
            response += f"\n\n📈 *Теперь линек:* {ValidationUtils.format_molts(result_msg)}"

        await callback.message.edit_text(
            response,
            reply_markup=None,
            parse_mode="Markdown"
        )

        logger.info(f"Пользователь {callback.from_user.id} записал {event_type} для питомца {pet_id}")
    else:
        await callback.message.edit_text(
            f"❌ *Ошибка записи {event_name}:*\n{result_msg}",
            parse_mode="Markdown"
        )

    await state.clear()
    await callback.answer()


@dp.callback_query(EventStates.confirming_event, F.data == "change_date")
async def process_change_date(callback: CallbackQuery, state: FSMContext):
    """Обработка изменения даты"""
    await state.set_state(EventStates.choosing_date_option)
    await ask_date_option(callback.message, state)
    await callback.answer()


@dp.callback_query(F.data == "cancel_event")
async def process_cancel_event(callback: CallbackQuery, state: FSMContext):
    """Отмена записи события"""
    await state.clear()
    await callback.message.edit_text(
        "❌ Запись события отменена.",
        reply_markup=None
    )
    await callback.answer()


async def cancel_event_process(message: Message, state: FSMContext):
    """Отмена записи события через текстовое сообщение"""
    await state.clear()
    await message.answer(
        "❌ Запись события отменена.",
        reply_markup=KeyboardManager.get_main_keyboard()
    )


# ========== УДАЛЕНИЕ ПИТОМЦА ==========
@dp.message(F.text == "🗑️ Удалить питомца")
async def delete_pet_start(message: Message, state: FSMContext):
    """Начало удаления питомца"""
    await DatabaseManager.ensure_user_in_db(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        language_code=message.from_user.language_code
    )

    pets = await DatabaseManager.get_user_pets(message.from_user.id)

    if not pets:
        await message.answer("У вас нет питомцев для удаления.", reply_markup=KeyboardManager.get_main_keyboard())
        return

    # Создаем клавиатуру с питомцами для удаления
    builder = InlineKeyboardBuilder()
    for pet in pets:
        display_name = pet.name or pet.species
        if len(display_name) > 20:
            display_name = display_name[:18] + ".."
        builder.button(
            text=f"❌ {display_name}",
            callback_data=f"select_del_{pet.id}"
        )

    builder.button(text="🔙 Отмена", callback_data="cancel_delete")
    builder.adjust(1)

    await state.set_state(DeletePetStates.choosing_pet)
    await message.answer(
        "Выберите питомца для удаления:",
        reply_markup=builder.as_markup()
    )


@dp.callback_query(DeletePetStates.choosing_pet, F.data.startswith("select_del_"))
async def confirm_deletion(callback: CallbackQuery, state: FSMContext):
    """Подтверждение удаления питомца"""
    pet_id = int(callback.data.split("_")[2])

    pet = await DatabaseManager.get_pet_by_id(pet_id, callback.from_user.id)

    if not pet:
        await callback.answer("❌ Питомец не найден.")
        return

    await state.update_data(pet_id=pet_id, pet_name=pet.name or pet.species)
    await state.set_state(DeletePetStates.confirming)

    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, удалить", callback_data="confirm_delete")
    builder.button(text="❌ Нет, отменить", callback_data="cancel_delete")
    builder.adjust(2)

    await callback.message.edit_text(
        f"⚠️ Вы уверены, что хотите удалить питомца?\n\n"
        f"Имя: {pet.name or 'Без имени'}\n"
        f"Вид: {pet.species}\n"
        f"Линек: {ValidationUtils.format_molts(pet.age)}\n"
        f"Добавлен: {pet.created_at.strftime('%d.%m.%Y')}\n\n"
        "❌ Это действие необратимо! Все данные будут удалены.",
        reply_markup=builder.as_markup()
    )


@dp.callback_query(DeletePetStates.confirming, F.data == "confirm_delete")
async def process_deletion(callback: CallbackQuery, state: FSMContext):
    """Обработка удаления питомца"""
    user_data = await state.get_data()
    pet_id = user_data.get('pet_id')
    pet_name = user_data.get('pet_name', 'Питомец')

    if not pet_id:
        await callback.answer("❌ Ошибка: ID питомца не найден.")
        await state.clear()
        return

    success = await DatabaseManager.delete_pet(pet_id, callback.from_user.id)

    if success:
        await callback.message.edit_text(
            f"✅ Питомец {pet_name} успешно удалён.\n"
            f"Все данные о кормлении, линьке и уборке удалены."
        )
    else:
        await callback.message.edit_text(
            "❌ Произошла ошибка при удалении питомца."
        )

    await state.clear()


@dp.callback_query(F.data == "cancel_delete")
async def cancel_delete(callback: CallbackQuery, state: FSMContext):
    """Отмена удаления"""
    await state.clear()
    await callback.message.edit_text(
        "❌ Удаление отменено.",
        reply_markup=None
    )
    await callback.answer()


# ========== СТАТИСТИКА ==========
@dp.message(F.text == "📊 Статистика")
async def show_statistics(message: Message):
    """Показать статистику бота"""
    await DatabaseManager.ensure_user_in_db(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        language_code=message.from_user.language_code
    )

    pets = await DatabaseManager.get_user_pets(message.from_user.id)
    pets_count = len(pets)

    # Считаем события
    feeding_count = sum(1 for p in pets if p.last_feeding)
    cleaning_count = sum(1 for p in pets if p.last_cleaning)
    molt_count = sum(1 for p in pets if p.last_molt)

    # Считаем общее количество линек у всех питомцев
    total_molts = 0
    for pet in pets:
        try:
            molts_match = re.search(r'(\d+)', pet.age)
            if molts_match:
                total_molts += int(molts_match.group(1))
        except:
            pass

    # Находим самого старшего (с наибольшим количеством линек)
    oldest_info = ""
    if pets:
        def get_molts(pet):
            try:
                molts_match = re.search(r'(\d+)', pet.age)
                return int(molts_match.group(1)) if molts_match else 0
            except:
                return 0

        oldest_pet = max(pets, key=get_molts)
        oldest_molts = get_molts(oldest_pet)
        if oldest_molts > 0:
            oldest_info = f"\n• Самый старший: {oldest_pet.name or oldest_pet.species} ({ValidationUtils.format_molts(oldest_pet.age)})"

    statistics_text = (
        "📊 *Статистика бота:*\n\n"
        f"👤 Пользователь: {message.from_user.full_name or 'Не указано'}\n"
        f"🆔 ID: {message.from_user.id}\n\n"
        f"🕷️ Питомцев всего: {pets_count}\n"
        f"🍽️ Записей кормления: {feeding_count}\n"
        f"🧹 Записей уборки: {cleaning_count}\n"
        f"🔄 Записей линьки: {molt_count}\n"
        f"📈 Всего линек у всех питомцев: {total_molts}"
        f"{oldest_info}\n\n"
        "*Особенность:* Возраст считается в количестве линек!\n"
        "*Новое:* Можно выбирать дату для событий!"
    )

    await message.answer(statistics_text, parse_mode="Markdown", reply_markup=KeyboardManager.get_main_keyboard())


# ========== НЕИЗВЕСТНЫЕ КОМАНДЫ ==========
@dp.message()
async def handle_unknown(message: Message):
    """Обработка неизвестных команд"""
    await message.answer(
        "🤔 Я не понял вашу команду.\n"
        "Используйте кнопки меню или команду /help",
        reply_markup=KeyboardManager.get_main_keyboard()
    )


# ========== ЗАПУСК БОТА ==========
async def migrate_existing_data():
    """Миграция существующих данных"""
    try:
        async with async_session() as session:
            # Находим всех user_id из таблицы pets, которых нет в таблице users
            pets_query = select(Pet.user_id).distinct()
            pets_result = await session.execute(pets_query)
            all_pet_user_ids = {user_id for (user_id,) in pets_result.all()}

            users_query = select(User.id)
            users_result = await session.execute(users_query)
            existing_user_ids = {user_id for (user_id,) in users_result.all()}

            missing_user_ids = all_pet_user_ids - existing_user_ids

            if missing_user_ids:
                logger.info(f"Найдено {len(missing_user_ids)} пользователей с питомцами, но без записи в users")
                print(f"🔍 Найдено {len(missing_user_ids)} пользователей с питомцами, но без записи в users")

                for user_id in missing_user_ids:
                    try:
                        chat_member = await bot.get_chat(user_id)
                        user = User(
                            id=user_id,
                            username=chat_member.username,
                            first_name=chat_member.first_name,
                            last_name=chat_member.last_name,
                            last_active=datetime.now()
                        )
                    except Exception as e:
                        logger.warning(f"Не удалось получить данные пользователя {user_id}: {e}")
                        user = User(
                            id=user_id,
                            first_name="Пользователь",
                            last_active=datetime.now()
                        )

                    session.add(user)

                await session.commit()
                logger.info(f"Добавлено {len(missing_user_ids)} пользователей в базу")
                print(f"✅ Добавлено {len(missing_user_ids)} пользователей в базу")
            else:
                logger.info("Все пользователи с питомцами уже есть в базе")
                print("✅ Все пользователи с питомцами уже есть в базе")

    except Exception as e:
        logger.error(f"Ошибка миграции данных: {e}")
        print(f"❌ Ошибка миграции данных: {e}")


async def main():
    """Главная функция запуска бота"""
    print("=" * 50)
    print("🕷️ Запуск бота для ухода за паукообразными и членистоногими")
    print("📈 С подсчетом возраста в линьках")
    print("🗓️ С возможностью выбора даты для событий")
    print("🛠️ С панелью администратора")
    print(f"🔑 Токен: {BOT_TOKEN[:10]}...")
    print(f"👑 Администратор: {ADMIN_ID}")
    print("=" * 50)

    # Инициализация БД
    try:
        await init_db()
        print("✅ База данных инициализирована")

        # Миграция существующих данных
        print("🔄 Проверка и миграция существующих данных...")
        await migrate_existing_data()

        # Проверим, есть ли администратор в базе
        async with async_session() as session:
            admin = await session.get(User, ADMIN_ID)
            if admin:
                print(f"✅ Администратор найден в базе: {admin.first_name} (@{admin.username})")
            else:
                print("⚠️ Администратор не найден в базе. Будет добавлен при первом использовании /admin")
    except Exception as e:
        print(f"❌ Ошибка инициализации БД: {e}")
        import traceback
        traceback.print_exc()
        return

    # Запуск бота
    try:
        bot_info = await bot.get_me()
        print("✅ Бот запущен и ожидает сообщений...")
        print("=" * 50)
        print(f"🤖 Имя бота: {bot_info.first_name}")
        print(f"🔗 Ссылка: https://t.me/{bot_info.username}")
        print("=" * 50)
        print("📱 Откройте Telegram и перейдите по ссылке выше")
        print("👉 Нажмите START и используйте кнопки меню!")
        print("=" * 50)

        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)

    except Exception as e:
        print(f"❌ Ошибка при запуске бота: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("Бот остановлен")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n✅ Бот остановлен пользователем")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")