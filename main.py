# main.py
import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from typing import Dict, Any

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, CallbackQuery, FSInputFile,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

# -------------------------------
# CONFIG - ⚠️ O'zgartiring
# -------------------------------
TOKEN = "8454294847:AAGqXlH02wmGNMXuAHMRxlXj0AvlSDNG9Hs"  # <-- bot tokenni o'zgartiring agar kerak bo'lsa
CHANNEL_ID = "-1003083593639"                             # <-- kanal id
ADMIN_ID = 123456789                                      # <-- o'zingizning telegram ID'ingiz
SHOW_MENU_AFTER_CONTACT = False                           # True bo'lsa kontaktdan keyin menyu chiqadi

# -------------------------------
# Logging
# -------------------------------
LOG_FILE = "bot.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# -------------------------------
# Files & Bot init
# -------------------------------
TEMP_SOURCE_FILE = Path("temp_sources.json")
USERS_FILE = Path("users.json")
WEEKLY_FILE = Path("weekly_users.json")
MONTHLY_FILE = Path("monthly_users.json")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# -------------------------------
# FSM States
# -------------------------------
class SourceForm(StatesGroup):
    waiting_for_other = State()

# -------------------------------
# Helper: JSON load/save
# -------------------------------
def safe_load_json(path: Path) -> Any:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        logger.warning("JSON decode error for %s — returning empty", path)
        return {}

def safe_save_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

# -------------------------------
# Temp sources helpers
# -------------------------------
def _load_temp_sources() -> Dict[str, str]:
    return safe_load_json(TEMP_SOURCE_FILE) or {}

def _save_temp_sources(data: Dict[str, str]) -> None:
    safe_save_json(TEMP_SOURCE_FILE, data)

def _pop_temp_source(user_id: str) -> str:
    data = _load_temp_sources()
    val = data.pop(user_id, None)
    _save_temp_sources(data)
    return val or "❌ Ko'rsatilmagan"

# -------------------------------
# Persistent user saving (users.json + weekly/monthly)
# -------------------------------
def save_user_to_files(user_dict: Dict[str, Any]) -> None:
    users = safe_load_json(USERS_FILE) or []
    # update or append
    existing = next((u for u in users if u.get("id") == user_dict["id"]), None)
    if existing:
        existing.update(user_dict)
    else:
        users.append(user_dict)
    # sort by joined_at
    try:
        users.sort(key=lambda x: x.get("joined_at", ""))
    except Exception:
        pass
    safe_save_json(USERS_FILE, users)

    # regenerate weekly/monthly
    weekly = defaultdict(list)
    monthly = defaultdict(list)
    for u in users:
        try:
            dt = datetime.strptime(u.get("joined_at"), "%Y-%m-%d %H:%M:%S")
            year, week, _ = dt.isocalendar()
            weekly[f"{year}-week{week}"].append(u)
            monthly[f"{dt.year}-{dt.month:02}"].append(u)
        except Exception:
            continue
    safe_save_json(WEEKLY_FILE, weekly)
    safe_save_json(MONTHLY_FILE, monthly)

# -------------------------------
# Keyboards
# -------------------------------
def menu_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="ℹ Biz haqimizda", callback_data="about")
    kb.button(text="👨‍🏫 O‘qituvchilar", callback_data="teachers")
    kb.button(text="🗺️ Manzil", callback_data="location")
    kb.button(text="📞 Admin bilan aloqa", callback_data="contact_admin")
    kb.button(text="✍️ Qabulga yozilish", callback_data="register")
    kb.adjust(2)
    return kb.as_markup()

def contact_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="📱 Qo‘ng‘iroq qilish", callback_data="call_admin")
    kb.button(text="✍️ Telegramdan yozish", url="https://t.me/Master_Dragon_1")
    kb.button(text="⬅️ Ortga", callback_data="back_menu")
    kb.adjust(1)
    return kb.as_markup()

def subjects_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="🇬🇧 Ingliz tili", callback_data="subject_english")
    kb.button(text="🧮 Matematika", callback_data="subject_math")
    kb.button(text="💻 IT", callback_data="subject_it")
    kb.button(text="⬅️ Ortga", callback_data="back_menu")
    kb.adjust(1)
    return kb.as_markup()

def source_keyboard():
    kb = InlineKeyboardBuilder()
    kb.button(text="📸 Instagramdan", callback_data="source_instagram")
    kb.button(text="📢 Telegramdan", callback_data="source_telegram")
    kb.button(text="👨‍👩‍👦 Tanishlar/qarindoshlar", callback_data="source_friends")
    kb.button(text="✍️ Boshqa", callback_data="source_other")
    kb.adjust(1)
    return kb.as_markup()

# -------------------------------
# Start handler: ask source first
# -------------------------------
@dp.message(CommandStart())
async def start_cmd(message: Message, state: FSMContext):
    try:
        await message.answer(
            "👋 *Assalomu alaykum!* \n\n"
            "🎓 *Cambridge Innovatsion School* ga xush kelibsiz!\n\n"
            "❓ *Biz haqimizda qayerdan eshitdingiz?*\n\n"
            "Fikringiz biz uchun muhim",
            reply_markup=source_keyboard(),
            parse_mode="Markdown"
        )
        logger.info("Asked source question to user %s (%s)", message.from_user.full_name, message.from_user.id)
    except Exception as e:
        logger.exception("start_cmd error: %s", e)

# -------------------------------
# Source callbacks
# -------------------------------
@dp.callback_query(F.data.startswith("source_"))
async def process_source(call: CallbackQuery, state: FSMContext):
    user_id = str(call.from_user.id)
    data = _load_temp_sources()
    source_map = {
        "source_instagram": "📸 Instagram",
        "source_telegram": "📢 Telegram",
        "source_friends": "👨‍👩‍👦 Tanishlar yoki qarindoshlar",
    }

    try:
        if call.data in source_map:
            data[user_id] = source_map[call.data]
            _save_temp_sources(data)
            await call.message.answer("✅ Rahmat! Sizning javobingiz yozib olindi.")
            await send_admin_new_user_partial(call.message.from_user, data[user_id])
            await call.message.answer("Biz haqimizda sizga kerakli barcha ma'lumotlarni shu yerdan topasiz deb umid qilamiz!", reply_markup=menu_keyboard())
            await call.answer()
            logger.info("Saved quick source for %s: %s", user_id, data[user_id])

        elif call.data == "source_other":
            await call.message.answer(
                "✍️ Iltimos, biz haqimizda qayerdan bilganingizni aniq yozib qoldiring.\n"
                "Bu ma'lumot biz uchun juda muhim 🙏"
            )
            await state.set_state(SourceForm.waiting_for_other)
            await call.answer()
            logger.info("User %s selected 'other' for source", user_id)

    except Exception as e:
        logger.exception("process_source error: %s", e)
        await call.answer("Xatolik yuz berdi. Iltimos qayta urinib ko'ring.", show_alert=True)

# -------------------------------
# Handle free-text "other" source
# -------------------------------
@dp.message(SourceForm.waiting_for_other)
async def process_other_source(message: Message, state: FSMContext):
    user_id = str(message.from_user.id)
    try:
        data = _load_temp_sources()
        data[user_id] = f"📝 {message.text}"
        _save_temp_sources(data)
        await message.answer("✅ Rahmat! Javobingiz yozib olindi.")
        await send_admin_new_user_partial(message.from_user, data[user_id])
        await message.answer("Biz haqimizda sizga kerakli barcha ma'lumotlarni shu yerdan topasiz deb umid qilamiz!", reply_markup=menu_keyboard())
        await state.clear()
        logger.info("Saved 'other' source for %s: %s", user_id, data[user_id])
    except Exception as e:
        logger.exception("process_other_source error: %s", e)
        await message.answer("Xatolik yuz berdi, iltimos qayta urinib ko'ring.")

# -------------------------------
# When user shares contact - save full record
# -------------------------------
@dp.message(F.contact)
async def contact_handler(message: Message):
    try:
        contact = message.contact
        user_id_str = str(message.from_user.id)
        # get and remove temp source (we pop it)
        temp_source = _pop_temp_source(user_id_str)

        user_record = {
            "id": message.from_user.id,
            "full_name": message.from_user.full_name,
            "username": f"@{message.from_user.username}" if message.from_user.username else "yo'q",
            "phone": contact.phone_number if contact and contact.phone_number else "❌ Telefon raqam yo'q",
            "source": temp_source,
            "joined_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        save_user_to_files(user_record)

        # forward to CHANNEL (gracefully)
        channel_text = (
            f"👤 Full Name: {user_record['full_name']}\n"
            f"🆔 Username: {user_record['username']}\n"
            f"📱 Phone: {user_record['phone']}\n"
            f"📊 Biz haqimizda manba: {user_record['source']}\n"
            f"🕒 Qo'shilgan vaqti: {user_record['joined_at']}"
        )
        try:
            await bot.send_message(CHANNEL_ID, channel_text)
        except Exception:
            logger.warning("Unable to send message to channel %s", CHANNEL_ID)

        # Notify admin with full info
        await send_admin_full_record(user_record)

        # confirmation to user
        await message.answer(
            "✅ Raqamingiz qabul qilindi!\n\n"
            "📌 Tez orada siz bilan bog‘lanamiz.",
            reply_markup=ReplyKeyboardRemove()
        )

        # optionally show menu after contact (configurable)
        if SHOW_MENU_AFTER_CONTACT:
            await message.answer("Biz haqimizda sizga kerakli barcha ma'lumotlarni shu yerdan topasiz deb umid qilamiz!", reply_markup=menu_keyboard())

        logger.info("Saved contact for user %s", user_record["id"])

    except Exception as e:
        logger.exception("contact_handler error: %s", e)
        await message.answer("Xatolik yuz berdi. Iltimos keyinroq urinib ko‘ring.")

# -------------------------------
# Menu & callbacks
# -------------------------------
@dp.callback_query()
async def callbacks(call: CallbackQuery):
    data = call.data
    try:
        if data == "about":
            # try sending a PDF if available, otherwise a branded text + image if present
            sent = False
            try:
                pdf_path = Path("cmis-compressed.pdf")
                if pdf_path.exists():
                    pdf = FSInputFile(str(pdf_path))
                    await call.message.answer_document(pdf, caption="📖 Cambridge Innovatsion School haqida to'liq ma'lumot")
                    sent = True
            except Exception:
                logger.warning("Failed to send PDF")

            if not sent:
                # fallback informative message
                await call.message.answer(
                    "📖 *Biz haqimizda*\n\n"
                    "Cambridge Innovatsion School — sifatli ta'lim, malakali o'qituvchilar va amaliy yondashuv.\n"
                    "Siz bu yerdan darslar, narxlar, jadval va o'qituvchilar haqida to'liq ma'lumot olasiz.",
                    parse_mode="Markdown"
                )

        elif data == "teachers":
            await call.message.answer("👩‍🏫 Qaysi fan o'qituvchilarini ko'rmoqchisiz?", reply_markup=subjects_keyboard())

        elif data == "subject_english":
            photo = FSInputFile("teachers/teacher2.jpg") if Path("teachers/teacher2.jpg").exists() else None
            caption = (
                "━━━━━━━━━━━━━━━━━━━━\n"
                "👩‍🏫 *Hayitali T*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "📌 Mutaxassisligi: *Ingliz tili grammatikasi*\n"
                "📚 Darslar: Speaking, Writing, Grammar, IELTS tayyorlov\n"
                "📅 Tajriba: 5+ yil"
            )
            if photo:
                await call.message.answer_photo(photo=photo, caption=caption, parse_mode="Markdown")
            else:
                await call.message.answer(caption, parse_mode="Markdown")

        elif data == "subject_math":
            photo = FSInputFile("teachers/teacher3.jpg") if Path("teachers/teacher3.jpg").exists() else None
            caption = (
                "━━━━━━━━━━━━━━━━━━━━\n"
                "👨‍🏫 *Razzoqov Shahboz*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "📌 Mutaxassisligi: *Matematika & Mnemonika*\n"
                "📚 Darslar: Matematika, SAT, Mental arifmetika\n"
                "📅 Tajriba: 7 yil"
            )
            if photo:
                await call.message.answer_photo(photo=photo, caption=caption, parse_mode="Markdown")
            else:
                await call.message.answer(caption, parse_mode="Markdown")

        elif data == "subject_it":
            photo = FSInputFile("teachers/teacher1.jpg") if Path("teachers/teacher1.jpg").exists() else None
            caption = (
                "━━━━━━━━━━━━━━━━━━━━\n"
                "👨‍💻 *Polatov Bunyodbek*\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "📌 Mutaxssisligi: *IT va Web Full Stack*\n"
                "📚 Darslar: Kompyuter savodxonligi, Python, JS, Django\n"
                "📅 Tajriba: 4 yil"
            )
            if photo:
                await call.message.answer_photo(photo=photo, caption=caption, parse_mode="Markdown")
            else:
                await call.message.answer(caption, parse_mode="Markdown")

        elif data == "back_menu":
            await call.message.answer("🏠 Asosiy menyuga qaytdingiz.", reply_markup=menu_keyboard())

        elif data == "location":
            # send location or textual fallback
            try:
                await call.message.answer_location(latitude=40.3849179, longitude=71.257808)
            except Exception:
                await call.message.answer("📍 Manzil: Toshkent shahri, Chilonzor tumani, 7-mavze")

        elif data == "contact_admin":
            await call.message.answer("📞 Admin bilan bog'lanish uchun variantlardan birini tanlang:", reply_markup=contact_keyboard())

        elif data == "call_admin":
            await call.message.answer("📱 Qo'ng'iroq uchun raqam: +998901234567")

        elif data == "register":
            contact_button = KeyboardButton(text="📞 Kontaktni ulashish", request_contact=True)
            keyboard = ReplyKeyboardMarkup(keyboard=[[contact_button]], resize_keyboard=True, one_time_keyboard=True)
            await call.message.answer("📱 Iltimos, telefon raqamingizni ulashing:", reply_markup=keyboard)
            await call.answer()
            return

        await call.answer()
    except Exception as e:
        logger.exception("callbacks handler error: %s", e)
        await call.answer("Xatolik yuz berdi", show_alert=True)

# -------------------------------
# Admin notifications
# -------------------------------
async def send_admin_new_user_partial(user, source_text: str):
    try:
        text = (
            "📈 *Yangi manba javobi*\n\n"
            f"👤 Ism: *{user.full_name}*\n"
            f"🆔 ID: `{user.id}`\n"
            f"📊 Manba: {source_text}\n\n"
            "_Note: foydalanuvchi telefonini yuborganida to'liq ma'lumot saqlanadi._"
        )
        await bot.send_message(ADMIN_ID, text, parse_mode="Markdown")
    except Exception:
        logger.exception("send_admin_new_user_partial failed")

async def send_admin_full_record(user_record: Dict[str, Any]):
    try:
        text = (
            "📥 *Yangi foydalanuvchi qo'shildi!*\n\n"
            f"👤 Ism: *{user_record['full_name']}*\n"
            f"🆔 ID: `{user_record['id']}`\n"
            f"📱 Telefon: `{user_record['phone']}`\n"
            f"📊 Manba: {user_record['source']}\n"
            f"🕒 Qo'shilgan vaqti: {user_record['joined_at']}\n"
            f"🔗 Username: {user_record['username']}"
        )
        await bot.send_message(ADMIN_ID, text, parse_mode="Markdown")
    except Exception:
        logger.exception("send_admin_full_record failed")

# -------------------------------
# Run bot
# -------------------------------
async def main():
    logger.info("Bot ishga tushmoqda...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

# -------------------------------
# Run bot (Webhook mode for Render)
# -------------------------------
import os
from aiohttp import web

async def handle(request):
    try:
        update = await request.json()
        await dp.feed_webhook_update(bot, update)
    except Exception as e:
        logger.exception("Webhook handle error: %s", e)
    return web.Response()

async def on_startup(app):
    try:
        webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/webhook"
        await bot.set_webhook(webhook_url)
        logger.info("Webhook set to %s", webhook_url)
    except Exception as e:
        logger.exception("on_startup error: %s", e)

async def on_shutdown(app):
    await bot.session.close()
    logger.info("Bot session closed")

app = web.Application()
app.router.add_post("/webhook", handle)
app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", 10000)))

