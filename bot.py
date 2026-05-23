from flask import Flask
from threading import Thread
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove
)

from aiogram.fsm.storage.memory import MemoryStorage

import os
import asyncio
import csv
from datetime import datetime

# ==========================================
# TOKEN
# ==========================================

TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ==========================================
# КРАСИВЫЕ КНОПКИ
# ==========================================

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="🐕 Сообщить о стае")
        ],
        [
            KeyboardButton(text="🗺 Карта"),
            KeyboardButton(text="ℹ️ Помощь")
        ]
    ],
    resize_keyboard=True
)

location_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(
                text="📍 Отправить геолокацию",
                request_location=True
            )
        ]
    ],
    resize_keyboard=True
)

# ==========================================
# ХРАНЕНИЕ ДАННЫХ
# ==========================================

user_data = {}

# ==========================================
# START
# ==========================================

@dp.message(Command("start"))
async def start_handler(message: types.Message):

    text = (
        "🐾 <b>Лапа Карта</b>\n\n"
        "Помогите сделать город безопаснее для людей и животных.\n\n"
        "Через этого бота можно:\n"
        "• сообщить о стае собак\n"
        "• отметить опасную зону\n"
        "• помочь волонтёрам быстрее реагировать\n\n"
        "👇 Выберите действие:"
    )

    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=main_keyboard
    )

# ==========================================
# ПОМОЩЬ
# ==========================================

@dp.message(F.text == "ℹ️ Помощь")
async def help_handler(message: types.Message):

    text = (
        "ℹ️ <b>Как пользоваться ботом</b>\n\n"
        "1️⃣ Нажмите «Сообщить о стае»\n"
        "2️⃣ Отправьте геолокацию\n"
        "3️⃣ Прикрепите фото\n"
        "4️⃣ Укажите количество собак\n"
        "5️⃣ Опишите ситуацию\n\n"
        "Спасибо за помощь 🐾"
    )

    await message.answer(
        text,
        parse_mode="HTML"
    )

# ==========================================
# КАРТА
# ==========================================

@dp.message(F.text == "🗺 Карта")
async def map_handler(message: types.Message):

    try:

        import pandas as pd
        import folium
        from aiogram.types import FSInputFile

        # ==========================================
        # ЧИТАЕМ CSV
        # ==========================================

        df = pd.read_csv(
            "reports.csv",
            header=None,
            names=[
                "time",
                "lat",
                "lon",
                "dogs",
                "aggression",
                "comment",
                "photo"
            ]
        )

        # ==========================================
        # ОБРАБОТКА КООРДИНАТ
        # ==========================================

        df["lat"] = pd.to_numeric(
            df["lat"],
            errors="coerce"
        )

        df["lon"] = pd.to_numeric(
            df["lon"],
            errors="coerce"
        )

        df = df.dropna(subset=["lat", "lon"])

        # ==========================================
        # КАРТА ТЮМЕНИ
        # ==========================================

        m = folium.Map(
            location=[57.1522, 65.5272],
            zoom_start=12
        )

        # ==========================================
        # ДОБАВЛЯЕМ ТОЧКИ
        # ==========================================

        for _, row in df.iterrows():

            color = "red"

            if str(row["aggression"]).lower() == "нет":
                color = "green"

            popup_text = f"""
            Время: {row['time']}
            
            Собак: {row['dogs']}
            
            Агрессия: {row['aggression']}
            
            Комментарий: {row['comment']}
            """

            folium.Marker(
                location=[
                    row["lat"],
                    row["lon"]
                ],
                popup=popup_text,
                tooltip="🐾 Лапа Карта",
                icon=folium.Icon(color=color)
            ).add_to(m)

        # ==========================================
        # СОХРАНЯЕМ HTML
        # ==========================================

        m.save("map.html")

        # ==========================================
        # ОТПРАВЛЯЕМ ФАЙЛ
        # ==========================================

        file = FSInputFile("map.html")

        await message.answer_document(
            file,
            caption="🗺 Карта наблюдений"
        )

    except Exception as e:

        print(e)

        await message.answer(
            f"❌ Ошибка карты:\n{e}"
        )

# ==========================================
# СООБЩИТЬ О СТАЕ
# ==========================================

@dp.message(F.text == "🐕 Сообщить о стае")
async def report_handler(message: types.Message):

    user_data[message.from_user.id] = {}

    await message.answer(
        "📍 Отправьте геолокацию стаи:",
        reply_markup=location_keyboard
    )

# ==========================================
# ГЕОЛОКАЦИЯ
# ==========================================

@dp.message(F.location)
async def location_handler(message: types.Message):

    user_id = message.from_user.id

    user_data[user_id]["latitude"] = message.location.latitude
    user_data[user_id]["longitude"] = message.location.longitude

    await message.answer(
        "📸 Теперь отправьте фото собак.",
        reply_markup=ReplyKeyboardRemove()
    )

# ==========================================
# ФОТО
# ==========================================

@dp.message(F.photo)
async def photo_handler(message: types.Message):

    user_id = message.from_user.id

    photo_id = message.photo[-1].file_id

    user_data[user_id]["photo"] = photo_id

    await message.answer(
        "🐕 Сколько собак вы увидели?"
    )

# ==========================================
# КОЛИЧЕСТВО СОБАК
# ==========================================

@dp.message(F.text.regexp(r'^\d+$'))
async def dogs_count_handler(message: types.Message):

    user_id = message.from_user.id

    if "dogs_count" not in user_data[user_id]:

        user_data[user_id]["dogs_count"] = message.text

        await message.answer(
            "⚠️ Есть ли агрессия?\n\n"
            "Напишите:\n"
            "Да / Нет"
        )

# ==========================================
# АГРЕССИЯ
# ==========================================

@dp.message(F.text.lower().in_(["да", "нет"]))
async def aggression_handler(message: types.Message):

    user_id = message.from_user.id

    if "aggression" not in user_data[user_id]:

        user_data[user_id]["aggression"] = message.text

        await message.answer(
            "✍️ Добавьте комментарий:\n\n"
            "Например:\n"
            "• возле школы\n"
            "• бегают за людьми\n"
            "• есть щенки"
        )

# ==========================================
# КОММЕНТАРИЙ + СОХРАНЕНИЕ
# ==========================================

@dp.message(F.text)
async def comment_handler(message: types.Message):

    try:

        user_id = message.from_user.id

        if user_id not in user_data:
            return

        data = user_data[user_id]

        # Проверяем все поля
        required_fields = [
            "latitude",
            "longitude",
            "photo",
            "dogs_count",
            "aggression"
        ]

        for field in required_fields:

            if field not in data:
                await message.answer(
                    f"❌ Ошибка: отсутствует поле {field}"
                )
                return

        # Сохраняем комментарий
        data["comment"] = message.text

        # Время
        data["time"] = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        # ==========================================
        # СОХРАНЕНИЕ CSV
        # ==========================================

        with open(
            "reports.csv",
            "a",
            newline="",
            encoding="utf-8"
        ) as file:

            writer = csv.writer(file)

            writer.writerow([
                data["time"],
                data["latitude"],
                data["longitude"],
                data["dogs_count"],
                data["aggression"],
                data["comment"],
                data["photo"]
            ])

        # ==========================================
        # УСПЕШНОЕ СООБЩЕНИЕ
        # ==========================================

        await message.answer(
            "✅ Сообщение успешно сохранено!\n\n"
            "Спасибо за помощь проекту «Лапа Карта» 🐾",
            reply_markup=main_keyboard
        )

        # Очищаем данные
        del user_data[user_id]

    except Exception as e:

        print("ОШИБКА:", e)

        await message.answer(
            f"❌ Произошла ошибка:\n{e}"
        )

# ==========================================
# ЗАПУСК
# ==========================================

async def main():

    print("🐾 Бот запущен...")

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())