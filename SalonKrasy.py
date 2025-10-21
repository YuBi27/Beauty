import asyncio
import logging
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

# === НАЛАШТУВАННЯ ===
API_TOKEN = "8113426901:AAErFwTH485nUDkhKV0Co9tEupXSdwEU32M"
ADMIN_ID = 313113979  # твій ID

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Тимчасове сховище
user_states = {}
appointments = {}  # {user_id: {"data": {...}, "status": "pending/approved/denied"}}

# === КНОПКИ ===
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💅 Записатись на послугу", callback_data="new_request")],
        [InlineKeyboardButton(text="📩 Зв'язок з адміністратором", url="https://t.me/yuriiyurii27")]
    ])

def confirm_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Відправити адміну", callback_data="send_admin")],
        [InlineKeyboardButton(text="❌ Скасувати", callback_data="cancel")]
    ])

def admin_reply_menu(user_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Погодити", callback_data=f"approve_{user_id}"),
            InlineKeyboardButton(text="❌ Відхилити", callback_data=f"deny_{user_id}")
        ]
    ])

def back_to_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="↩️ Повернутись в меню", callback_data="back_to_menu")]
    ])

# === СТАРТ ===
@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_states.pop(message.from_user.id, None)
    await message.answer(
        "👋 Вітаємо в салоні краси 💖\n"
        "Тут ви можете легко записатись на послуги:\n"
        "💅 Манікюр\n🦶 Педикюр\n💆 Косметолог\n\n"
        "Оберіть дію нижче:",
        reply_markup=main_menu()
    )

# === НОВИЙ ЗАПИС ===
@dp.callback_query(lambda c: c.data == "new_request")
async def start_request(callback: CallbackQuery):
    user_states[callback.from_user.id] = {"step": "ask_service", "data": {}}
    await callback.message.answer("📌 Оберіть послугу (манікюр / педикюр / косметолог):")

# === ОБРОБКА КРОКІВ ===
@dp.message()
async def handle_steps(message: Message):
    user_id = message.from_user.id
    if user_id not in user_states:
        await message.answer("🤖 Я не зрозумів. Введіть /start, щоб почати.")
        return

    state = user_states[user_id]
    step = state["step"]

    if step == "ask_service":
        state["data"]["service"] = message.text
        state["step"] = "ask_date"
        await message.answer("📅 Вкажіть дату процедури (у форматі ДД.ММ.РРРР):")

    elif step == "ask_date":
        try:
            date_obj = datetime.strptime(message.text, "%d.%m.%Y")
            state["data"]["date"] = date_obj
            state["step"] = "ask_time"
            await message.answer("⏰ Вкажіть час процедури (наприклад: 14:30):")
        except ValueError:
            await message.answer("⚠️ Невірний формат дати! Введіть у форматі ДД.ММ.РРРР")

    elif step == "ask_time":
        try:
            datetime.strptime(message.text, "%H:%M")
            state["data"]["time"] = message.text
            state["step"] = "ask_contact"
            await message.answer("📱 Вкажіть ваші контактні дані (телефон або Telegram):")
        except ValueError:
            await message.answer("⚠️ Невірний формат часу! Введіть у форматі ГГ:ХХ")

    elif step == "ask_contact":
        state["data"]["contact"] = message.text
        state["step"] = "confirm"
        data = state["data"]
        summary = (
            f"📋 <b>Ваш запис:</b>\n\n"
            f"💅 Послуга: {data['service']}\n"
            f"📅 Дата: {data['date'].strftime('%d.%m.%Y')}\n"
            f"⏰ Час: {data['time']}\n"
            f"📱 Контакт: {data['contact']}\n\n"
            "Якщо все вірно — підтвердіть:"
        )
        await message.answer(summary, reply_markup=confirm_menu(), parse_mode="HTML")

# === ВІДПРАВИТИ АДМІНУ ===
@dp.callback_query(lambda c: c.data == "send_admin")
async def send_admin(callback: CallbackQuery):
    user_id = callback.from_user.id
    state = user_states.get(user_id)

    if not state or state["step"] != "confirm":
        await callback.answer("🚫 Немає активного запису.", show_alert=True)
        return

    data = state["data"]
    appointments[user_id] = {"data": data, "status": "pending"}

    text = (
        f"📨 <b>Новий запис від @{callback.from_user.username or callback.from_user.full_name}:</b>\n\n"
        f"💅 Послуга: {data['service']}\n"
        f"📅 Дата: {data['date'].strftime('%d.%m.%Y')}\n"
        f"⏰ Час: {data['time']}\n"
        f"📱 Контакт: {data['contact']}"
    )

    await bot.send_message(ADMIN_ID, text, parse_mode="HTML", reply_markup=admin_reply_menu(user_id))
    await callback.message.edit_text("✅ Заявку відправлено адміну. Очікуйте підтвердження.", reply_markup=back_to_menu())
    user_states.pop(user_id, None)

# === АДМІН ПІДТВЕРДЖУЄ ЗАПИС ===
@dp.callback_query(F.data.startswith("approve_"))
async def approve_request(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    appointment = appointments.get(user_id)

    if not appointment:
        await callback.answer("Запис не знайдено.")
        return

    appointment["status"] = "approved"
    data = appointment["data"]

    # Повідомлення клієнту
    await bot.send_message(
        user_id,
        f"✅ Ваш запис підтверджено!\n\n"
        f"💅 Послуга: {data['service']}\n"
        f"📅 Дата: {data['date'].strftime('%d.%m.%Y')}\n"
        f"⏰ Час: {data['time']}"
    )

    await callback.message.edit_text(f"✅ Ви погодили запис користувача {user_id}")

    # Запуск нагадувань
    asyncio.create_task(schedule_reminders(user_id, data))

# === АДМІН ВІДХИЛЯЄ ЗАПИС ===
@dp.callback_query(F.data.startswith("deny_"))
async def deny_request(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[1])

    await callback.message.answer("✏️ Введіть причину відмови:")
    appointments[user_id]["status"] = "awaiting_reason"
    appointments[user_id]["admin_msg_id"] = callback.message.message_id

@dp.message()
async def get_denial_reason(message: Message):
    # Якщо адміністратор вводить причину
    if message.from_user.id == ADMIN_ID:
        for uid, app in appointments.items():
            if app.get("status") == "awaiting_reason":
                reason = message.text
                app["status"] = "denied"
                await bot.send_message(uid, f"❌ Ваш запис відхилено.\nПричина: {reason}")
                await message.answer("🚫 Відмову відправлено користувачу.")
                return

# === НАГАДУВАННЯ ===
async def schedule_reminders(user_id, data):
    appointment_datetime = datetime.strptime(
        f"{data['date'].strftime('%d.%m.%Y')} {data['time']}", "%d.%m.%Y %H:%M"
    )

    one_day_before = appointment_datetime - timedelta(days=1)
    one_hour_before = appointment_datetime - timedelta(hours=1)

    now = datetime.now()
    delay_day = (one_day_before - now).total_seconds()
    delay_hour = (one_hour_before - now).total_seconds()

    async def send_reminder(delay, text):
        if delay > 0:
            await asyncio.sleep(delay)
            await bot.send_message(user_id, text)

    asyncio.create_task(send_reminder(delay_day, "⏰ Нагадування! Завтра у вас процедура 💅"))
    asyncio.create_task(send_reminder(delay_hour, "⏰ Нагадування! Через годину у вас процедура 💖"))

# === ПОВЕРНЕННЯ В МЕНЮ ===
@dp.callback_query(lambda c: c.data == "back_to_menu")
async def back_to_main(callback: CallbackQuery):
    user_states.pop(callback.from_user.id, None)
    await callback.message.edit_text("🔙 Ви повернулися до головного меню.", reply_markup=main_menu())

# === СКАСУВАННЯ ===
@dp.callback_query(lambda c: c.data == "cancel")
async def cancel(callback: CallbackQuery):
    user_states.pop(callback.from_user.id, None)
    await callback.message.edit_text("❌ Запис скасовано.", reply_markup=main_menu())

# === ЗАПУСК ===
if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
 