# -*- coding: utf-8 -*-

import asyncio
import json
import os
import requests
from aiogram import Bot, Dispatcher
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

GIST_ID = os.getenv("GIST_ID")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GIST_FILENAME = "results.json"
GIST_API_URL = f"https://api.github.com/gists/{GIST_ID}" if GIST_ID else None

def load_results():
    if not GIST_ID or not GITHUB_TOKEN:
        print("GIST_ID или GITHUB_TOKEN не настроены")
        return {}
    
    try:
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        response = requests.get(GIST_API_URL, headers=headers)
        
        if response.status_code == 200:
            gist_data = response.json()
            file_content = gist_data["files"][GIST_FILENAME]["content"]
            return json.loads(file_content)
        else:
            print(f"Ошибка загрузки из Gist: {response.status_code}")
            return {}
    except Exception as e:
        print(f"Ошибка при загрузке: {e}")
        return {}

def save_results(data):
    if not GIST_ID or not GITHUB_TOKEN:
        print("GIST_ID или GITHUB_TOKEN не настроены")
        return
    
    try:
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        update_data = {
            "files": {
                GIST_FILENAME: {
                    "content": json.dumps(data, ensure_ascii=False, indent=4)
                }
            }
        }
        response = requests.patch(GIST_API_URL, headers=headers, json=update_data)
        
        if response.status_code == 200:
            print("Данные успешно сохранены в Gist")
        else:
            print(f"Ошибка сохранения в Gist: {response.status_code}")
    except Exception as e:
        print(f"Ошибка при сохранении: {e}")

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("Токен бота не найден в переменных окружения!")

ADMIN_IDS = [8167634087]

results = load_results()

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

questions = [
"1. Используете ли вы сложный пароль (буквы разного регистра, цифры, символы)?",
"2. Применяете ли вы разные пароли для разных сайтов?",
"3. Включена ли у вас двухфакторная аутентификация?",
"4. Проверяете ли вы адрес сайта перед вводом данных?",
"5. Проверяете ли вы ссылки перед открытием?",
"6. Удаляете ли вы личные данные из интернета?",
"7. Выполняете ли вы обновления безопасности?",
"8. Проверяете ли настройки приватности аккаунтов?",
"9. Используете ли антивирус?",
"10. Пользуетесь ли VPN?",
"11. Знаете ли вы что такое фишинг?",
"12. Проверяете ли разрешения приложений?",
"13. Выходите ли из аккаунтов на чужих устройствах?",
"14. Сообщаете ли о подозрительных ситуациях?",
"15. Думаете ли перед публикацией личной информации?"
]

answers = {
"Да": 2,
"Иногда": 1,
"Нет": 0
}

keyboard = ReplyKeyboardMarkup(
keyboard=[
[KeyboardButton(text="Да")],
[KeyboardButton(text="Иногда")],
[KeyboardButton(text="Нет")]
],
resize_keyboard=True
)

class TestStates(StatesGroup):
    question = State()

@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.update_data(score=0, q_index=0)
    await message.answer(
"Привет! 👋\n\n"
"Этот тест определит ваш уровень интернет безопасности.\n\n"
"Ответьте на 15 вопросов."
)
    await message.answer(questions[0], reply_markup=keyboard)
    await state.set_state(TestStates.question)

@dp.message(TestStates.question)
async def process_answer(message: Message, state: FSMContext):
    data = await state.get_data()
    q_index = data.get("q_index", 0)
    score = data.get("score", 0)

    if message.text in answers:
        score += answers[message.text]

    q_index += 1
    await state.update_data(score=score, q_index=q_index)

    if q_index < len(questions):
        await message.answer(questions[q_index], reply_markup=keyboard)
    else:
        if score <= 15:
            level = "Низкий уровень безопасности"
            rec = (
"• создавайте сложные уникальные пароли\n"
"• включите двухфакторную аутентификацию\n"
"• удалите лишние личные данные из интернета\n"
"• не открывайте подозрительные ссылки\n"
"• не используйте открытый Wi-Fi для важных данных"
)
        elif score <= 24:
            level = "Средний уровень безопасности"
            rec = (
"• усилите защиту аккаунтов\n"
"• регулярно проверяйте настройки приватности\n"
"• используйте антивирус\n"
"• избегайте сомнительных ссылок"
)
        else:
            level = "Высокий уровень безопасности"
            rec = (
"• продолжайте соблюдать правила безопасности\n"
"• регулярно обновляйте пароли\n"
"• делитесь знаниями о безопасности с другими"
        )

        await message.answer(
f"✅ Тест завершён\n\n"
f"Ваш результат: {score}/30\n"
f"Уровень: {level}\n\n"
f"Рекомендации:\n{rec}"
)

        global results
        results[str(message.from_user.id)] = {
        "name": message.from_user.full_name,
        "score": score,
        "level": level
        }
        save_results(results)

        await state.clear()

@dp.message(Command("admin"))
async def admin_panel(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Доступ запрещён")
        return

    current_results = load_results()
    if not current_results:
        await message.answer("Пока нет результатов")
        return

    text = "📊 Результаты пользователей:\n\n"
    for user in current_results.values():
        text += f"{user['name']} — {user['score']}/30 — {user['level']}\n"

    await message.answer(text)

async def main():
    print("Бот запускается...")
    if GIST_ID and GITHUB_TOKEN:
        print(f"Данные будут сохраняться в GitHub Gist: {GIST_ID}")
    else:
        print("ВНИМАНИЕ: GitHub Gist не настроен! Данные не сохранятся!")
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        print(f"Ошибка при запуске: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
