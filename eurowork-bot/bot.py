import asyncio
import logging
import math
import io
import os
import sys
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.filters.command import CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
import aiosqlite
from PIL import Image, ImageDraw, ImageFont


# ============ КАСТОМНЫЕ ЭМОДЗИ ============
from aiogram.types import MessageEntity

def build_msg_with_emoji(emoji_id: str, emoji_char: str, text: str):
    """Returns (full_text, entities) with custom emoji at start"""
    full_text = emoji_char + " " + text
    # Длина эмодзи в UTF-16
    utf16_len = len(emoji_char.encode('utf-16-le')) // 2
    entity = MessageEntity(
        type="custom_emoji",
        offset=0,
        length=utf16_len,
        custom_emoji_id=emoji_id
    )
    return full_text, [entity]

EMOJI_QUESTION1 = ("5258389638006984449", "🥂")
EMOJI_QUESTION2 = ("5258113901106580375", "⌛️")
EMOJI_QUESTION3 = ("5314413943035278948", "🧠")
EMOJI_REFILL    = ("5258420634785947640", "🔄")
EMOJI_SUBMIT    = ("5258043150110301407", "📤")
EMOJI_DONE      = ("5260341314095947411", "✅")
EMOJI_CLOCK     = ("5258419835922030550", "🕔")
EMOJI_HEADER    = ("5260341314095947411", "✅")

# ============ НАСТРОЙКИ ============
BOT_TOKEN = "8672395175:AAHrYXhhbEyHnqZNWYAo5G8ElyFVdkROb4k"
ADMIN_ID = 8182201162
MANUAL_LINK = "https://t.me/+ZyG0Bos9gLU1YjEy"
MENTOR_1_NAME = "aleksmakaer"
MENTOR_2_NAME = "theOnewhoG"
EU_FLAG_URL = "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b7/Flag_of_Europe.svg/1280px-Flag_of_Europe.svg.png"

if sys.platform == 'win32':
    FONT_BOLD = 'C:/Windows/Fonts/arialbd.ttf'
    if not os.path.exists(FONT_BOLD):
        FONT_BOLD = 'C:/Windows/Fonts/arial.ttf'
else:
    FONT_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
# ===================================

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Словарь для отслеживания сообщений с профилем (user_id -> message_id)
profile_messages = {}


# ============ ГЕНЕРАЦИЯ КАРТОЧКИ ПРОФИЛЯ ============
def generate_profile_card(username: str, days: int, profits_count: int, profits_sum: float) -> bytes:
    W, H = 960, 540

    bg = Image.new('RGB', (W, H))
    bg_draw = ImageDraw.Draw(bg)
    for y in range(H):
        t = y / H
        bg_draw.line([(0, y), (W, y)], fill=(int(8+t*10), int(12+t*18), int(30+t*45)))

    img = bg.convert('RGBA')

    # WATERMARK
    wm_font = ImageFont.truetype(FONT_BOLD, 105)
    wm_img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(wm_img).text((W//2, H//2), 'EUROWORK', font=wm_font, fill=(255, 255, 255, 16), anchor='mm')
    img = Image.alpha_composite(img, wm_img)
    draw = ImageDraw.Draw(img)

    # EU LOGO
    cx, cy, r = W//2, 82, 52
    draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=(0, 48, 150, 255))
    for i in range(12):
        angle = math.radians(i*30 - 90)
        sx = cx + int(36*math.cos(angle))
        sy = cy + int(36*math.sin(angle))
        pts = []
        for j in range(5):
            ao = math.radians(j*72 - 90)
            ai = math.radians(j*72 + 36 - 90)
            pts += [(sx+5*math.cos(ao), sy+5*math.sin(ao)), (sx+2*math.cos(ai), sy+2*math.sin(ai))]
        draw.polygon(pts, fill=(255, 204, 0, 255))

    draw.text((W//2, 155), 'EuroWork Team', font=ImageFont.truetype(FONT_BOLD, 20), fill=(160, 190, 255, 255), anchor='mm')

    # Функция для правильного склонения слова "день"
    def get_days_text(day_count: int) -> str:
        if day_count % 10 == 1 and day_count % 100 != 11:
            return f"{day_count} день"
        elif day_count % 10 in [2, 3, 4] and day_count % 100 not in [12, 13, 14]:
            return f"{day_count} дня"
        else:
            return f"{day_count} дней"

    # 4 CARDS
    card_data = [
        ('ДНИ В КОМАНДЕ', get_days_text(days)),
        ('КОЛ-ВО ПРОФИТОВ', str(profits_count)),
        ('СУММА ПРОФИТОВ', f'{profits_sum:.2f} EUR'),
        ('ИМЯ ВОРКЕРА', username[:12]),
    ]
    card_w, card_h = 192, 148
    gap = 18
    start_x = (W - (4*card_w + 3*gap)) // 2
    card_y = 195

    label_font = ImageFont.truetype(FONT_BOLD, 12)
    val_font = ImageFont.truetype(FONT_BOLD, 28)

    for i, (label, value) in enumerate(card_data):
        x = start_x + i*(card_w+gap)
        sh = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle([x+4, card_y+4, x+card_w+4, card_y+card_h+4], radius=14, fill=(0, 0, 0, 70))
        img = Image.alpha_composite(img, sh)
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle([x, card_y, x+card_w, card_y+card_h], radius=14, fill=(15, 22, 55, 240), outline=(45, 85, 200, 255), width=2)
        draw.rounded_rectangle([x+20, card_y-2, x+card_w-20, card_y+3], radius=3, fill=(80, 130, 255, 255))
        draw.text((x+card_w//2, card_y+30), label, font=label_font, fill=(120, 155, 230, 255), anchor='mm')
        draw.line([(x+18, card_y+50), (x+card_w-18, card_y+50)], fill=(40, 70, 170, 255), width=1)
        draw.text((x+card_w//2, card_y+100), value, font=val_font, fill=(240, 245, 255, 255), anchor='mm')

    buf = io.BytesIO()
    img.convert('RGB').save(buf, format='PNG')
    buf.seek(0)
    return buf.read()


# ============ БД ============
async def init_db():
    """Инициализирует БД с миграцией схемы"""
    async with aiosqlite.connect("eurowork.db") as db:
        # Создаём таблицу если её нет
        await db.execute("""
            CREATE TABLE IF NOT EXISTS workers (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                join_date TEXT,
                profits_count INTEGER DEFAULT 0,
                profits_sum REAL DEFAULT 0.0,
                mentor TEXT DEFAULT '',
                approved INTEGER DEFAULT 0,
                application_submitted INTEGER DEFAULT 0
            )
        """)
        
        # Проверяем существование таблицы и получаем информацию о колонках
        try:
            async with db.execute("PRAGMA table_info(workers)") as cur:
                columns = await cur.fetchall()
                column_names = [col[1] for col in columns]
                
                # Если колонки нет - добавляем её
                if 'application_submitted' not in column_names:
                    logging.info("Добавляю колонку application_submitted в БД...")
                    await db.execute(
                        "ALTER TABLE workers ADD COLUMN application_submitted INTEGER DEFAULT 0"
                    )
                    logging.info("✅ Миграция завершена успешно")
        except Exception as e:
            logging.error(f"Ошибка при проверке схемы БД: {e}")
        
        await db.commit()

async def get_worker(user_id: int):
    async with aiosqlite.connect("eurowork.db") as db:
        async with db.execute("SELECT * FROM workers WHERE user_id = ?", (user_id,)) as cur:
            return await cur.fetchone()

async def create_worker(user_id: int, username: str):
    async with aiosqlite.connect("eurowork.db") as db:
        await db.execute(
            "INSERT OR IGNORE INTO workers (user_id, username, join_date) VALUES (?, ?, ?)",
            (user_id, username or "unknown", datetime.now().strftime("%Y-%m-%d"))
        )
        await db.commit()

async def set_mentor(user_id: int, mentor: str):
    async with aiosqlite.connect("eurowork.db") as db:
        await db.execute("UPDATE workers SET mentor = ? WHERE user_id = ?", (mentor, user_id))
        await db.commit()

async def approve_worker(user_id: int):
    async with aiosqlite.connect("eurowork.db") as db:
        await db.execute("UPDATE workers SET approved = 1 WHERE user_id = ?", (user_id,))
        await db.commit()

async def set_profits(user_id: int, count: int, amount: float):
    async with aiosqlite.connect("eurowork.db") as db:
        await db.execute(
            "UPDATE workers SET profits_count = ?, profits_sum = ? WHERE user_id = ?",
            (count, amount, user_id)
        )
        await db.commit()

async def set_join_date(user_id: int, join_date: str):
    """Устанавливает дату присоединения к команде"""
    async with aiosqlite.connect("eurowork.db") as db:
        await db.execute(
            "UPDATE workers SET join_date = ? WHERE user_id = ?",
            (join_date, user_id)
        )
        await db.commit()

async def get_all_workers():
    async with aiosqlite.connect("eurowork.db") as db:
        async with db.execute("SELECT * FROM workers") as cur:
            return await cur.fetchall()

async def get_worker_by_username(username: str):
    async with aiosqlite.connect("eurowork.db") as db:
        async with db.execute(
            "SELECT * FROM workers WHERE LOWER(username) = LOWER(?)", (username.lstrip("@"),)
        ) as cur:
            return await cur.fetchone()


# ============ ХЕЛПЕРЫ ============
def days_in_team(join_date: str) -> int:
    try:
        joined = datetime.strptime(join_date, "%Y-%m-%d")
        return (datetime.now() - joined).days
    except:
        return 0


# ============ ФОНОВОЕ ОБНОВЛЕНИЕ КАРТИНОК ============
async def auto_update_profiles():
    """Автоматически обновляет профиль-карточки каждый день"""
    while True:
        try:
            await asyncio.sleep(3600)  # Проверяем каждый час
            
            workers = await get_all_workers()
            if not workers:
                continue
            
            for worker in workers:
                user_id, username, join_date, profits_count, profits_sum, mentor, approved = worker[:7]
                
                # Если воркер одобрен и у нас есть его сообщение с профилем
                if approved == 1 and user_id in profile_messages:
                    try:
                        days = days_in_team(join_date)
                        img_bytes = generate_profile_card(username, days, int(profits_count), float(profits_sum))
                        
                        # Обновляем медиа
                        await bot.edit_message_media(
                            chat_id=user_id,
                            message_id=profile_messages[user_id],
                            media=types.InputMediaPhoto(
                                media=BufferedInputFile(img_bytes, filename="profile.png")
                            )
                        )
                        logging.info(f"✅ Профиль {username} (ID: {user_id}) автоматически обновлён")
                    except Exception as e:
                        logging.error(f"Ошибка обновления профиля {user_id}: {e}")
                        # Удаляем из словаря если сообщение было удалено
                        if user_id in profile_messages:
                            del profile_messages[user_id]
        except Exception as e:
            logging.error(f"Ошибка в фоновом обновлении: {e}")
            await asyncio.sleep(60)


# ============ FSM ============
class Reg(StatesGroup):
    q1 = State()
    q2 = State()
    q3 = State()

class AdminAddProfit(StatesGroup):
    username = State()
    data = State()

class AdminSetDate(StatesGroup):
    username = State()
    date = State()


# ============ КЛАВИАТУРЫ ============
def kb_main():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Профиль", callback_data="profile"),
         InlineKeyboardButton(text="EuroWork V1 Manual", callback_data="manual")],
        [InlineKeyboardButton(text="Выбрать наставника", callback_data="mentor_menu")],
    ])

def kb_mentor():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Наставник 1 — @{MENTOR_1_NAME}", callback_data="pick_mentor_1")],
        [InlineKeyboardButton(text=f"Наставник 2 — @{MENTOR_2_NAME}", callback_data="pick_mentor_2")],
        [InlineKeyboardButton(text="Назад", callback_data="back_main")],
    ])

def kb_profile():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Обновить вручную", callback_data="refresh_profile")],
        [InlineKeyboardButton(text="Назад", callback_data="back_main")],
    ])

def kb_manual():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Открыть мануал", url=MANUAL_LINK)],
        [InlineKeyboardButton(text="Назад", callback_data="back_main")],
    ])

def kb_start():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Начать", callback_data="reg_start")]
    ])

def kb_refill():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Перезаполнить", callback_data="reg_start", icon_custom_emoji_id="5258420634785947640")]
    ])

def kb_submit():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Подать", callback_data="reg_submit", icon_custom_emoji_id="5258043150110301407")],
        [InlineKeyboardButton(text="Перезаполнить", callback_data="reg_start", icon_custom_emoji_id="5258420634785947640")],
    ])


# ============ ГЛАВНОЕ МЕНЮ ============
async def send_main_menu(chat_id: int, edit_msg: types.Message = None):
    text = "<b>МЕНЮ</b>\nEuroWork Team"
    if edit_msg:
        try:
            await edit_msg.edit_caption(caption=text, reply_markup=kb_main(), parse_mode="HTML")
            return
        except:
            try:
                await edit_msg.delete()
            except:
                pass
    await bot.send_photo(chat_id, photo=EU_FLAG_URL, caption=text, reply_markup=kb_main(), parse_mode="HTML")


# ============ /start ============
@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    first_name = message.from_user.first_name or 'Воркер'
    username = message.from_user.username or first_name
    await create_worker(user_id, first_name)

    try:
        await message.delete()
    except:
        pass

    worker = await get_worker(user_id)

    # Если админ или одобренный воркер - открыть главное меню
    if user_id == ADMIN_ID or (worker and worker[6] == 1):
        await bot.send_photo(user_id, photo=EU_FLAG_URL, caption="<b>МЕНЮ</b>\nEuroWork Team", reply_markup=kb_main(), parse_mode="HTML")
        return

    # Если заявка уже была отправлена и ещё не одобрена - показать экран ожидания
    if worker and worker[6] == 0 and len(worker) > 7 and worker[7] == 1:
        await bot.send_message(
            user_id,
            "Ваша заявка на рассмотрении. Ожидайте подтверждения администратора."
        )
        return

    if user_id != ADMIN_ID:
        await bot.send_message(ADMIN_ID, f"Новый пользователь зашёл в бота\nИмя: {first_name}\nНик: @{username}\nID: {user_id}")

    await bot.send_message(
        user_id,
        "<b>Добро пожаловать в EuroWork Team!</b>\n\nДля вступления в команду необходимо отправить заявку",
        reply_markup=kb_start(),
        parse_mode="HTML"
    )


# ============ РЕГИСТРАЦИЯ ============
@dp.callback_query(F.data == "reg_start")
async def reg_start(cb: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(Reg.q1)
    try:
        await cb.message.delete()
    except:
        pass
    txt, ents = build_msg_with_emoji(*EMOJI_QUESTION1, "Вопрос №1\nОткуда вы узнали о команде?")
    msg = await bot.send_message(cb.from_user.id, txt, entities=ents, reply_markup=kb_refill())
    await state.update_data(last_bot_msg_id=msg.message_id)

@dp.message(Reg.q1)
async def reg_q1(message: types.Message, state: FSMContext):
    data = await state.get_data()
    try:
        await bot.delete_message(message.chat.id, data.get("last_bot_msg_id"))
    except:
        pass
    try:
        await message.delete()
    except:
        pass
    await state.update_data(a1=message.text)
    await state.set_state(Reg.q2)
    txt, ents = build_msg_with_emoji(*EMOJI_QUESTION2, "Вопрос №2\nСколько времени готовы уделять работе?")
    msg = await bot.send_message(message.chat.id, txt, entities=ents, reply_markup=kb_refill())
    await state.update_data(last_bot_msg_id=msg.message_id)

@dp.message(Reg.q2)
async def reg_q2(message: types.Message, state: FSMContext):
    data = await state.get_data()
    try:
        await bot.delete_message(message.chat.id, data.get("last_bot_msg_id"))
    except:
        pass
    try:
        await message.delete()
    except:
        pass
    await state.update_data(a2=message.text)
    await state.set_state(Reg.q3)
    txt, ents = build_msg_with_emoji(*EMOJI_QUESTION3, "Вопрос №3\nБыл ли у вас опыт в похожем проекте?")
    msg = await bot.send_message(message.chat.id, txt, entities=ents, reply_markup=kb_refill())
    await state.update_data(last_bot_msg_id=msg.message_id)

@dp.message(Reg.q3)
async def reg_q3(message: types.Message, state: FSMContext):
    data = await state.get_data()
    try:
        await bot.delete_message(message.chat.id, data.get("last_bot_msg_id"))
    except:
        pass
    try:
        await message.delete()
    except:
        pass
    await state.update_data(a3=message.text)
    data = await state.get_data()
    await state.set_state(None)
    sum_text = f"Заявка на вход в команду сформирована\n\nВаши ответы:\n\n№1: {data['a1']}\n№2: {data['a2']}\n№3: {data['a3']}\n\nПодать заявку?"
    txt, ents = build_msg_with_emoji(*EMOJI_HEADER, sum_text)
    msg = await bot.send_message(message.chat.id, txt, entities=ents, reply_markup=kb_submit())
    await state.update_data(last_bot_msg_id=msg.message_id)

@dp.callback_query(F.data == "reg_submit")
async def reg_submit(cb: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user = cb.from_user
    username = user.username or user.first_name
    
    # Устанавливаем флаг что заявка отправлена
    async with aiosqlite.connect("eurowork.db") as db:
        await db.execute("UPDATE workers SET application_submitted = 1 WHERE user_id = ?", (user.id,))
        await db.commit()
    
    await bot.send_message(
        ADMIN_ID,
        f"Новая заявка!\n\nНик: @{username}\nID: {user.id}\n\n"
        f"№1: {data.get('a1','—')}\n№2: {data.get('a2','—')}\n№3: {data.get('a3','—')}\n\n"
        f"Одобрить: /approve_{user.id}"
    )
    try:
        await cb.message.delete()
    except:
        pass
    txt, ents = build_msg_with_emoji(*EMOJI_CLOCK, "Заявка успешно подана\nОжидайте решения администрации...")
    await bot.send_message(user.id, txt, entities=ents)
    await state.clear()


# ============ МЕНЮ ============
@dp.callback_query(F.data == "back_main")
async def back_main(cb: types.CallbackQuery):
    await send_main_menu(cb.from_user.id, edit_msg=cb.message)


# ============ ПРОФИЛЬ ============
@dp.callback_query(F.data == "profile")
async def show_profile(cb: types.CallbackQuery):
    worker = await get_worker(cb.from_user.id)
    if not worker:
        await cb.answer("Сначала пройдите регистрацию", show_alert=True)
        return

    user_id, username, join_date, profits_count, profits_sum, mentor, approved = worker[:7]
    days = days_in_team(join_date)

    # Генерируем карточку
    img_bytes = generate_profile_card(username, days, int(profits_count), float(profits_sum))
    photo = BufferedInputFile(img_bytes, filename="profile.png")

    caption = (
        f"Имя: {username}\n"
        f"ID: {user_id}\n"
        f"Дней в команде: {days}\n"
        f"Наставник: {mentor or 'не выбран'}\n"
        f"Профиты: {profits_count} шт | {profits_sum:.2f} EUR\n"
        f"Статус: {'✅ Одобрен' if approved else '⏳ На рассмотрении'}"
    )

    try:
        await cb.message.delete()
    except:
        pass
    
    msg = await bot.send_photo(cb.from_user.id, photo=photo, caption=caption, reply_markup=kb_profile())
    # Сохраняем ID сообщения для автоматического обновления
    profile_messages[user_id] = msg.message_id

@dp.callback_query(F.data == "refresh_profile")
async def refresh_profile(cb: types.CallbackQuery):
    """Обновляет карточку профиля вручную"""
    worker = await get_worker(cb.from_user.id)
    if not worker:
        await cb.answer("Ошибка загрузки профиля", show_alert=True)
        return

    user_id, username, join_date, profits_count, profits_sum, mentor, approved = worker[:7]
    days = days_in_team(join_date)

    # Генерируем карточку
    img_bytes = generate_profile_card(username, days, int(profits_count), float(profits_sum))

    caption = (
        f"Имя: {username}\n"
        f"ID: {user_id}\n"
        f"Дней в команде: {days}\n"
        f"Наставник: {mentor or 'не выбран'}\n"
        f"Профиты: {profits_count} шт | {profits_sum:.2f} EUR\n"
        f"Статус: {'✅ Одобрен' if approved else '⏳ На рассмотрении'}"
    )

    try:
        await cb.message.edit_media(
            media=types.InputMediaPhoto(
                media=BufferedInputFile(img_bytes, filename="profile.png")
            )
        )
        await cb.message.edit_caption(caption=caption, reply_markup=kb_profile())
        await cb.answer("✅ Профиль обновлён", show_alert=False)
    except Exception as e:
        logging.error(f"Ошибка при обновлении профиля: {e}")
        await cb.answer("Ошибка обновления", show_alert=True)


# ============ МАНУАЛ ============
@dp.callback_query(F.data == "manual")
async def show_manual(cb: types.CallbackQuery):
    try:
        await cb.message.delete()
    except:
        pass
    await bot.send_message(
        cb.from_user.id,
        "EuroWork V1 Manual\n\nДоступ к мануалу по работе:",
        reply_markup=kb_manual()
    )


# ============ ВЫБОР НАСТАВНИКА ============
@dp.callback_query(F.data == "mentor_menu")
async def mentor_menu(cb: types.CallbackQuery):
    try:
        await cb.message.edit_caption(caption="Выберите наставника:", reply_markup=kb_mentor())
    except:
        try:
            await cb.message.delete()
        except:
            pass
        await bot.send_photo(cb.from_user.id, photo=EU_FLAG_URL, caption="Выберите наставника:", reply_markup=kb_mentor())

@dp.callback_query(F.data.in_(["pick_mentor_1", "pick_mentor_2"]))
async def pick_mentor(cb: types.CallbackQuery):
    mentor = MENTOR_1_NAME if cb.data == "pick_mentor_1" else MENTOR_2_NAME
    await set_mentor(cb.from_user.id, f"@{mentor}")
    username = cb.from_user.username or cb.from_user.first_name
    await bot.send_message(ADMIN_ID, f"Воркер выбрал наставника\n@{username} (ID: {cb.from_user.id})\nНаставник: @{mentor}")
    await cb.answer(f"Наставник @{mentor} выбран!", show_alert=True)
    await send_main_menu(cb.from_user.id, edit_msg=cb.message)


# ============ ADMIN ============
@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer(
        "Админ панель",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Список воркеров", callback_data="admin_list")],
            [InlineKeyboardButton(text="Добавить профит", callback_data="admin_add_profit")],
            [InlineKeyboardButton(text="Изменить дату присоединения", callback_data="admin_set_date")],
        ])
    )

@dp.message(lambda m: m.text and m.text.startswith("/approve_"))
async def approve_cmd(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        user_id = int(message.text.split("_")[1])
        worker = await get_worker(user_id)
        if not worker:
            await message.answer("Воркер не найден")
            return
        await approve_worker(user_id)
        await message.answer(f"Воркер {user_id} одобрен!")
        txt, ents = build_msg_with_emoji(*EMOJI_DONE, "Ваша заявка была одобрена.\nНажмите /start для продолжения.")
        await bot.send_message(user_id, txt, entities=ents)
    except Exception as e:
        await message.answer(f"Ошибка: {e}")

@dp.callback_query(F.data == "admin_list")
async def admin_list(cb: types.CallbackQuery):
    if cb.from_user.id != ADMIN_ID:
        return
    workers = await get_all_workers()
    if not workers:
        await cb.answer("Нет воркеров", show_alert=True)
        return
    text = "Список воркеров:\n\n"
    for w in workers:
        uid, uname, jdate, pc, ps, mentor, approved = w[:7]
        days = days_in_team(jdate)
        text += f"@{uname} (ID: {uid})\nДней: {days} | {pc} профитов | {ps:.2f} EUR\nНаставник: {mentor or '—'} | {'Одобрен' if approved else 'Ожидает'}\n\n"
    await cb.message.answer(text)

@dp.callback_query(F.data == "admin_add_profit")
async def admin_add_profit_start(cb: types.CallbackQuery, state: FSMContext):
    if cb.from_user.id != ADMIN_ID:
        return
    await cb.message.answer("Введите ник воркера (с @ или без) или ID:")
    await state.set_state(AdminAddProfit.username)

@dp.message(AdminAddProfit.username)
async def admin_profit_username(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    
    search_input = message.text.strip()
    worker = None
    
    # Пытаемся найти по ID
    if search_input.isdigit():
        worker = await get_worker(int(search_input))
    else:
        # Пытаемся найти по юзернейму
        worker = await get_worker_by_username(search_input)
    
    if not worker:
        await message.answer(f"Воркер {search_input} не найден. Попробуйте ещё раз:")
        return
    
    await state.update_data(target_id=worker[0], target_name=worker[1])
    await message.answer(
        f"Воркер: @{worker[1]} (ID: {worker[0]})\n"
        f"Текущие профиты: {worker[3]} шт, {worker[4]:.2f} EUR\n\n"
        f"Введите новые значения в формате: <кол-во> <сумма>\nПример: 5 250.00"
    )
    await state.set_state(AdminAddProfit.data)

@dp.message(AdminAddProfit.data)
async def admin_profit_set(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        parts = message.text.split()
        count = int(parts[0])
        amount = float(parts[1])
        data = await state.get_data()
        target_id = data["target_id"]
        target_name = data["target_name"]
        await set_profits(target_id, count, amount)
        await message.answer(f"✅ Профиты @{target_name} обновлены: {count} шт, {amount:.2f} EUR")
        await bot.send_message(target_id, f"Ваши профиты обновлены!\nКол-во: {count}\nСумма: {amount:.2f} EUR")
    except Exception as e:
        await message.answer(f"Ошибка: {e}")
    await state.clear()

@dp.callback_query(F.data == "admin_set_date")
async def admin_set_date_start(cb: types.CallbackQuery, state: FSMContext):
    if cb.from_user.id != ADMIN_ID:
        return
    await cb.message.answer("Введите ник воркера (с @ или без) или ID:")
    await state.set_state(AdminSetDate.username)

@dp.message(AdminSetDate.username)
async def admin_set_date_username(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    
    search_input = message.text.strip()
    worker = None
    
    # Пытаемся найти по ID
    if search_input.isdigit():
        worker = await get_worker(int(search_input))
    else:
        # Пытаемся найти по юзернейму
        worker = await get_worker_by_username(search_input)
    
    if not worker:
        await message.answer(f"Воркер {search_input} не найден. Попробуйте ещё раз:")
        return
    
    current_days = days_in_team(worker[2])
    await state.update_data(target_id=worker[0], target_name=worker[1])
    await message.answer(
        f"Воркер: @{worker[1]} (ID: {worker[0]})\n"
        f"Текущая дата присоединения: {worker[2]} ({current_days} дней)\n\n"
        f"Введите новую дату в формате: YYYY-MM-DD\nПример: 2024-01-15"
    )
    await state.set_state(AdminSetDate.date)

@dp.message(AdminSetDate.date)
async def admin_set_date_value(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        new_date = message.text.strip()
        # Проверяем формат даты
        datetime.strptime(new_date, "%Y-%m-%d")
        
        data = await state.get_data()
        target_id = data["target_id"]
        target_name = data["target_name"]
        
        await set_join_date(target_id, new_date)
        new_days = days_in_team(new_date)
        
        await message.answer(f"✅ Дата присоединения @{target_name} обновлена на {new_date} ({new_days} дней)")
        await bot.send_message(target_id, f"Ваша дата присоединения обновлена!\nНовая дата: {new_date}\nДней в команде: {new_days}")
    except ValueError:
        await message.answer("❌ Неверный формат даты! Используйте YYYY-MM-DD\nПопробуйте ещё раз:")
        return
    except Exception as e:
        await message.answer(f"Ошибка: {e}")
    await state.clear()


# ============ ПОЛУЧИТЬ ID ЭМОДЗИ (только для админа) ============
@dp.message(F.entities)
async def get_emoji_id(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    custom_emoji = [e for e in message.entities if e.type == "custom_emoji"]
    if custom_emoji:
        text = "Твои эмодзи ID:\n\n"
        for entity in custom_emoji:
            e_id = entity.custom_emoji_id
            char = message.text[entity.offset:entity.offset + entity.length]
            text += f"{char} — `{e_id}`\n"
        await message.answer(text, parse_mode="MarkdownV2")

# ============ ЗАПУСК ============
async def main():
    await init_db()
    
    # Запускаем фоновое обновление в отдельной задаче
    asyncio.create_task(auto_update_profiles())
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())