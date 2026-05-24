import asyncio
import csv
from aiogram.filters import StateFilter
from datetime import datetime
from aiogram.types import WebAppInfo
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
    WebAppInfo,
    FSInputFile
)

import folium
import pandas as pd
import subprocess

# =========================
# TOKEN
# =========================
TOKEN = "8952313397:AAEEm_ebAhDerKqWzVdUVYmrnjz57IaUL1Y"

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())


# =========================
# FSM STATES
# =========================
class Report(StatesGroup):
    location = State()
    photo = State()
    dogs_count = State()
    aggression = State()
    comment = State()

# =========================
# KEYBOARDS
# =========================
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🐕 Сообщить о стае")],
        [KeyboardButton(text="🗺 Карта"), KeyboardButton(text="ℹ️ Помощь")]
    ],
    resize_keyboard=True
)

location_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📍 Отправить геолокацию", request_location=True)]
    ],
    resize_keyboard=True
)

aggression_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Да"), KeyboardButton(text="Нет")]
    ],
    resize_keyboard=True
)


# =========================
# START
# =========================
@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):

    await state.clear()

    await message.answer(
        "🐾 Лапа Карта",
        reply_markup=main_keyboard
)

# =========================
# HELP
# =========================
@dp.message(F.text == "ℹ️ Помощь")
async def help_handler(message: types.Message):

    text = (
        "🐾 <b>Помощь — Лапа Карта</b>\n\n"

        "Этот бот помогает отмечать места,\n"
        "где были замечены бездомные собаки.\n\n"

        "📌 <b>Как отправить сообщение:</b>\n\n"

        "1️⃣ Нажмите «🐕 Сообщить о стае»\n\n"

        "2️⃣ Отправьте геолокацию места\n\n"

        "3️⃣ Прикрепите фото собак\n\n"

        "4️⃣ Укажите количество собак\n\n"

        "5️⃣ Выберите:\n"
        "• Есть агрессия\n"
        "• Нет агрессии\n\n"

        "6️⃣ Напишите комментарий\n"
        "(например: возле школы,\n"
        "у гаражей, есть щенки и т.д.)\n\n"

        "🗺 <b>Карта</b>\n"
        "Во вкладке «Карта» можно посмотреть\n"
        "все отмеченные места.\n\n"

        "⚠️ <b>Важно:</b>\n"
        "Не отправляйте фейковые сообщения.\n"
        "Это мешает волонтёрам и другим людям.\n\n"

        "❤️ Спасибо за помощь проекту!"
    )

    await message.answer(
        text,
        parse_mode="HTML"
    )

# =========================
# START REPORT
# =========================
@dp.message(F.text == "🐕 Сообщить о стае")
async def report_handler(message: types.Message, state: FSMContext):

    await state.clear()

    await state.set_state(Report.location)

    await message.answer(
        "📍 Отправьте геолокацию стаи:",
        reply_markup=location_keyboard
    )
# =========================
# LOCATION
# =========================
@dp.message(StateFilter(Report.location), F.location)
async def location_handler(message: types.Message, state: FSMContext):

    await state.update_data(
        latitude=message.location.latitude,
        longitude=message.location.longitude
    )

    await state.set_state(Report.photo)

    await message.answer(
        "📸 Теперь отправьте фото собак.",
        reply_markup=ReplyKeyboardRemove()
    )
# =========================
# PHOTO
# =========================
@dp.message(StateFilter(Report.photo), F.photo)
async def photo_handler(message: types.Message, state: FSMContext):

    photo_id = message.photo[-1].file_id

    await state.update_data(photo=photo_id)

    await state.set_state(Report.dogs_count)

    await message.answer(
        "🐕 Сколько собак вы увидели?"
    )
# =========================
# DOG COUNT
# =========================
@dp.message(StateFilter(Report.dogs_count))
async def dogs_count_handler(message: types.Message, state: FSMContext):

    if not message.text:

        await message.answer(
            "Введите число собак."
        )
        return

    if not message.text.isdigit():

        await message.answer(
            "Введите число собак цифрами."
        )
        return

    await state.update_data(
        dogs_count=message.text
    )

    await state.set_state(Report.aggression)

    await message.answer(
        "⚠️ Есть ли агрессия?",
        reply_markup=aggression_keyboard
    )
# =========================
# AGGRESSION
# =========================
@dp.message(StateFilter(Report.aggression))
async def get_aggression(message: types.Message, state: FSMContext):

    if not message.text:

        await message.answer(
            "Нажмите кнопку Да или Нет"
        )
        return

    text = message.text.lower()

    if text not in ["да", "нет"]:

        await message.answer(
            "Выберите кнопку Да или Нет"
        )
        return

    await state.update_data(
        aggression=text
    )

    await state.set_state(Report.comment)

    await message.answer(
        "✍️ Напишите комментарий:",
        reply_markup=ReplyKeyboardRemove()
    )
# =========================
# COMMENT + SAVE
# =========================
@dp.message(StateFilter(Report.comment))
async def comment_handler(message: types.Message, state: FSMContext):

    if not message.text:

        await message.answer(
            "Напишите комментарий текстом."
        )
        return

    data = await state.get_data()

    data["comment"] = message.text
    data["time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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

    generate_map()

    upload_to_github()

    await state.clear()
    await message.answer(
        "✅ Сообщение успешно сохранено!\n\n"
        "Спасибо за помощь проекту 🐾",
        reply_markup=main_keyboard
    )

# =========================
# MAP
# =========================
@dp.message(F.text == "🗺 Карта")
async def map_handler(message: types.Message, state: FSMContext):

    await state.clear()

    web_app = WebAppInfo(
        url="https://Yakovvw.github.io/lapa-karta-bot/"
    )

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="🗺 Открыть карту",
                    web_app=web_app
                )
            ],
            [
                KeyboardButton(text="⬅️ Назад")
            ]
        ],
        resize_keyboard=True
    )

    await message.answer(
        "🗺 Нажмите кнопку ниже:",
        reply_markup=keyboard
    )


@dp.message(F.text == "⬅️ Назад")
async def back_handler(message: types.Message, state: FSMContext):

    await state.clear()

    await message.answer(
        "Главное меню:",
        reply_markup=main_keyboard
    )


# =========================
# RUN
# =========================
def generate_map():

    import pandas as pd

    df = pd.read_csv("reports.csv")

    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")

    df = df.dropna(subset=["lat", "lon"])

    markers_js = ""

    for _, row in df.iterrows():

        color = "red"

        if str(row["aggression"]).lower() == "нет":
            color = "green"

        markers_js += f"""
L.circleMarker([{row['lat']}, {row['lon']}], {{
    radius: 16,
    weight: 3,
    fillOpacity: 0.9,
    color: '{color}'
}}).addTo(map)
.bindPopup(`
🐕 Собак: {row['dogs']}<br>
⚠️ Агрессия: {row['aggression']}<br>
📝 {row['comment']}
`);
"""

    html = f"""
<!DOCTYPE html>
<html>
<head>

<meta charset="utf-8">

<title>Лапа Карта</title>

<link
rel="stylesheet"
href="https://unpkg.com/leaflet/dist/leaflet.css"
/>

<style>

body {{
    margin: 0;
}}

#map {{
    height: 100vh;
}}

</style>

</head>
<body>

<div id="map"></div>

<script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>

<script>

const map = L.map('map').setView([57.1522, 65.5272], 12);

L.tileLayer(
'https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',
{{
    maxZoom: 19
}}
).addTo(map);

{markers_js}

</script>

</body>
</html>
"""

    with open("index.html", "w", encoding="utf-8") as file:
        file.write(html)

def upload_to_github():

    try:

        subprocess.run(
            ["git", "add", "."],
            check=True
        )

        subprocess.run(
            ["git", "commit", "-m", "update map"],
            check=True
        )

        subprocess.run(
            ["git", "push"],
            check=True
        )

        print("GitHub updated!")

    except Exception as e:

        print("GitHub error:", e)
# =========================
# RUN
# =========================
async def main():

    await bot.delete_webhook(
        drop_pending_updates=True
    )

    print("Bot started...")

    await dp.start_polling(
    bot,
    polling_timeout=30
    )


if __name__ == "__main__":
    asyncio.run(main())