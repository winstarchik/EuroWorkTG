import asyncio
import logging
import os
from threading import Thread
from flask import Flask
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from groq import Groq

# --- КОНФИГУРАЦИЯ ---
TELEGRAM_TOKEN = "8725813902:AAHqum_d4IRhd1QTzjjat_GHdEAI-pTG_jk"
GROQ_API_KEY = "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"
ADMIN_ID = 8182201162 
VACANCY_FILE = "vacancies.txt"

client = Groq(api_key=GROQ_API_KEY)

# Загрузка вакансий из файла или дефолт
if os.path.exists(VACANCY_FILE):
    with open(VACANCY_FILE, "r", encoding="utf-8") as f:
        current_vacancies = f.read()
else:
    current_vacancies = "Разнорабочие на склады, Упаковщики, Сборщики заказов."

# --- ВЕБ-СЕРВЕР ДЛЯ АВТОПОДЪЕМА ---
app = Flask('')

@app.route('/')
def home():
    return "Euro-Work Bot is Alive!"

def run_web():
    # Hugging Face использует порт 7860 по умолчанию
    app.run(host='0.0.0.0', port=7860)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# --- ЛОГИКА БОТА ---
def get_system_prompt():
    return {
        "role": "system",
        "content": (
            "Ты — профессиональный ИИ-менеджер компании Euro-Work.\n"
            f"Актуальные вакансии: {current_vacancies}.\n"
            "Сайт: https://euro-work.vercel.app/\n"
            "Персонал: Алексей (@Aleksmakaer), Глеб (@glebshishkow).\n\n"
            "ПРАВИЛА: Приветствуй клиента, отвечай кратко (2-4 предложения) и по делу."
        )
    }

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
user_history = {}

def get_main_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="Вакансии"), types.KeyboardButton(text="📍 Адрес"))
    builder.row(types.KeyboardButton(text="🛡 Гарантии"), types.KeyboardButton(text="👥 Персонал"))
    builder.row(types.KeyboardButton(text="📝 Оставить заявку"))
    return builder.as_markup(resize_keyboard=True)

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user_history[message.from_user.id] = [get_system_prompt()]
    await message.answer("Здравствуйте! 👋 Euro-Work на связи. Чем могу помочь?", reply_markup=get_main_keyboard())

@dp.message()
async def handle_message(message: types.Message):
    global current_vacancies
    user_id = message.from_user.id
    
    # Бэкдор: обновление вакансий с сохранением в файл
    if user_id == ADMIN_ID and message.text.lower().startswith("обнови вакансии:"):
        new_vacs = message.text[16:].strip()
        current_vacancies = new_vacs
        with open(VACANCY_FILE, "w", encoding="utf-8") as f:
            f.write(new_vacs)
        user_history[user_id] = [get_system_prompt()]
        await message.answer("✅ Вакансии обновлены и сохранены.")
        return

    if user_id not in user_history:
        user_history[user_id] = [get_system_prompt()]
    
    user_history[user_id][0] = get_system_prompt()
    user_history[user_id].append({"role": "user", "content": message.text})
    
    if len(user_history[user_id]) > 8:
        user_history[user_id] = [get_system_prompt()] + user_history[user_id][-6:]

    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=user_history[user_id],
            temperature=0.6,
            max_tokens=400,
        )
        ai_response = completion.choices[0].message.content
        user_history[user_id].append({"role": "assistant", "content": ai_response})
        await message.answer(ai_response, parse_mode="Markdown", reply_markup=get_main_keyboard())
    except Exception:
        await message.answer("Заминка. Загляните на сайт: https://euro-work.vercel.app/")

async def main():
    keep_alive() # Запуск веб-сервера
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())