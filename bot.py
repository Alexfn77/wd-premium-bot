from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputFile
from aiogram.utils import executor

BOT_TOKEN = "8292107357:AAFkF7If0XZO5Lbs-OulC48R_DICNs_pizk"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)


# ===== ГЛАВНОЕ МЕНЮ =====
@dp.message_handler(commands=['start'])
async def start(message: types.Message):

    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("💎 WD Premium", callback_data="premium"),
        InlineKeyboardButton("📖 Каталог", callback_data="catalog"),
        InlineKeyboardButton("✨ История на заказ", callback_data="custom"),
        InlineKeyboardButton("✉ Менеджер WD", url="https://t.me/Ki1iWD")
    )

    photo = InputFile("cover.jpg")

    await bot.send_photo(
        message.chat.id,
        photo,
        caption=(
            "🖤 <b>WET DREAMS</b>\n"
            "<i>private premium story project</i>\n\n"

            "Закрытая цифровая библиотека\n"
            "авторских чувственных историй.\n\n"

            "<b>Выберите раздел ниже.</b>"
        ),
        parse_mode="HTML",
        reply_markup=keyboard
    )


# ===== WD PREMIUM =====
@dp.callback_query_handler(lambda c: c.data == "premium")
async def premium(callback_query: types.CallbackQuery):

    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("💎 1 месяц — 199 ₽", callback_data="sub1"),
        InlineKeyboardButton("💎 1.5 месяца — 279 ₽", callback_data="sub15"),
        InlineKeyboardButton("💎 2 месяца — 349 ₽", callback_data="sub2"),
        InlineKeyboardButton("⬅ Назад", callback_data="back")
    )

    photo = InputFile("premium.jpg")

    text = (
        "💎 <b>WD Premium</b>\n"
        "<i>private members club</i>\n\n"

        "Закрытый канал проекта WET DREAMS.\n\n"

        "Участники получают:\n\n"
        "🔒 эксклюзивные истории 18+\n"
        "🔥 более откровенные версии\n"
        "⚡ ранний доступ к новым публикациям\n"
        "🗂 архив Premium-материалов\n"
        "🗳 участие в голосованиях\n"
        "📖 бонусные мини-истории\n"
        "🔔 закрытые анонсы\n"
        "✨ 1 персональный заказ в месяц\n\n"

        "Большинство новых историй\n"
        "сначала публикуется в Premium.\n\n"

        "<b>Выберите формат доступа.</b>"
    )

    await bot.send_photo(
        callback_query.from_user.id,
        photo,
        caption=text,
        parse_mode="HTML",
        reply_markup=keyboard
    )


# ===== КАТАЛОГ =====
@dp.callback_query_handler(lambda c: c.data == "catalog")
async def catalog(callback_query: types.CallbackQuery):

    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("🔥 Ночное искушение", callback_data="story1"),
        InlineKeyboardButton("🕯 После полуночи", callback_data="story2"),
        InlineKeyboardButton("⬅ Назад", callback_data="back")
    )

    photo = InputFile("catalog.jpg")

    text = (
        "📖 <b>Каталог историй</b>\n"
        "<i>author collection</i>\n\n"

        "Каждая история — отдельная атмосфера\n"
        "и самостоятельная работа.\n\n"

        "Истории приобретаются отдельно\n"
        "и остаются в вашем доступе.\n\n"

        "<b>Выберите историю ниже.</b>"
    )

    await bot.send_photo(
        callback_query.from_user.id,
        photo,
        caption=text,
        parse_mode="HTML",
        reply_markup=keyboard
    )


# ===== ИСТОРИЯ 1 =====
@dp.callback_query_handler(lambda c: c.data == "story1")
async def story1(callback_query: types.CallbackQuery):

    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("💳 Приобрести — 3 USDT", callback_data="buy_story1"),
        InlineKeyboardButton("⬅ Назад", callback_data="catalog")
    )

    await bot.send_message(
        callback_query.from_user.id,
        "🔥 <b>Ночное искушение</b>\n\n"
        "Формат: PDF\n"
        "Объём: ~15 страниц\n\n"
        "<b>Полная версия доступна после покупки.</b>",
        parse_mode="HTML",
        reply_markup=keyboard
    )


# ===== ВЫДАЧА ФАЙЛА =====
@dp.callback_query_handler(lambda c: c.data == "buy_story1")
async def buy_story1(callback_query: types.CallbackQuery):

    file = InputFile("story1.pdf")

    await bot.send_message(
        callback_query.from_user.id,
        "💎 Оплата подтверждена.\n\nФайл доступен ниже."
    )

    await bot.send_document(
        callback_query.from_user.id,
        file
    )


# ===== ИСТОРИЯ НА ЗАКАЗ =====
@dp.callback_query_handler(lambda c: c.data == "custom")
async def custom(callback_query: types.CallbackQuery):

    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("✍ Обсудить заказ", url="https://t.me/Ki1iWD"),
        InlineKeyboardButton("⬅ Назад", callback_data="back")
    )

    photo = InputFile("custom.jpg")

    await bot.send_photo(
        callback_query.from_user.id,
        photo,
        caption=(
            "✨ <b>История на заказ</b>\n\n"
            "Персональная история,\n"
            "созданная по вашим пожеланиям.\n\n"
            "Каждый заказ обсуждается индивидуально."
        ),
        parse_mode="HTML",
        reply_markup=keyboard
    )


# ===== НАЗАД =====
@dp.callback_query_handler(lambda c: c.data == "back")
async def back(callback_query: types.CallbackQuery):
    await start(callback_query.message)


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)