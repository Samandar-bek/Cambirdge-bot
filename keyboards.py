from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup


# 🔹 Asosiy menyu
def menu_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="ℹ️ Biz haqimizda", callback_data="about")
    kb.button(text="👨‍🏫 O‘qituvchilar", callback_data="teachers")
    kb.button(text="🗺️ Manzil", callback_data="location")
    kb.button(text="📞 Admin bilan bog‘lanish", callback_data="contact_admin")
    kb.button(text="📝 Qabulga yozilish", callback_data="register")

    # Tugmalarni ikki qatorda chiroyli qilib joylashtiramiz
    kb.adjust(2, 2, 1)
    return kb.as_markup()


# 🔹 Admin bilan bog‘lanish
def contact_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📱 Qo‘ng‘iroq qilish", callback_data="call_admin")
    kb.button(text="✍️ Telegramdan yozish", url="https://t.me/Master_Dragon_1")
    kb.button(text="⬅️ Ortga", callback_data="back_menu")

    # Hammasi bitta ustunda tartib bilan chiqadi
    kb.adjust(1)
    return kb.as_markup()

