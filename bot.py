import os
import requests

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputFile
from aiogram.utils import executor

# ===== ТОКЕНЫ =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
CRYPTO_TOKEN = "561572:AAdgX8dZ3dqWIUcIi2LBccNdRV0zBKZF497"
ADMIN_ID = 7733841337

# ===== ИНИЦИАЛИЗАЦИЯ =====
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

def create_invoice(amount, description):
    url = "https://pay.crypt.bot/api/createInvoice"
    headers = {
        "Crypto-Pay-API-Token": CRYPTO_TOKEN
    }
    data = {
        "asset": "USDT",
        "amount": amount,
        "description": description
    }

    response = requests.post(url, headers=headers, json=data)
    result = response.json()

    if result["ok"]:
        return result["result"]["pay_url"]
    else:
        return None


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
        InlineKeyboardButton("💎 1 месяц — 3 USDT", callback_data="sub1"),
        InlineKeyboardButton("💎 2 месяца — 5 USDT", callback_data="sub2"),
        InlineKeyboardButton("💎 3 месяца — 7 USDT", callback_data="sub3"),
        InlineKeyboardButton("⬅ Назад", callback_data="back")
    )

    photo = InputFile("premium.jpg")

    text = (
        "💎 <b>WD Premium</b>\n"
        "<i>private members club</i>\n\n"

        "Закрытый доступ к самому откровенному контенту проекта WET DREAMS.\n\n"

        "Здесь нет ограничений —\n"
        "только то, что не публикуется в открытом доступе.\n\n"

        "Участники получают:\n\n"

        "🔒 эксклюзивные истории 18+\n"
        "🔥 максимально откровенный формат без цензуры\n"
        "⚡ доступ к новым публикациям раньше всех\n"
        "🗂 полный архив Premium-контента\n"
        "🗳 влияние на будущие истории\n"
        "📖 бонусные сцены и мини-истории\n"
        "🔔 закрытые анонсы\n\n"
        "✨ 1 персональная история в месяц\n"
        "(короткая, по вашей теме)\n\n"

        "💳 Оплата в USDT\n\n"

        "⏳ Доступ ограничен.\n\n"

        "<b>Выберите формат доступа.</b>"
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


# ===== SUB1 =====
@dp.callback_query_handler(lambda c: c.data == "sub1")
async def sub1(callback_query: types.CallbackQuery):

    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("💳 Перейти к оплате", callback_data="pay1"),
        InlineKeyboardButton("⬅ Назад", callback_data="premium")
    )

    photo = InputFile("1month.jpg")

    await bot.send_photo(
        callback_query.from_user.id,
        photo,
        caption=(
            "💎 <b>WD Premium — 1 месяц</b>\n\n"

            "Идеально, чтобы попробовать формат и погрузиться в атмосферу.\n\n"

            "Вы получите:\n"
            "🔒 доступ ко всему Premium-контенту\n"
            "🔥 самые откровенные истории без цензуры\n"
            "⚡ ранний доступ к новым публикациям\n"
            "📖 бонусные сцены\n\n"

            "⏳ Доступ: 30 дней\n"
            "💳 Стоимость: 3 USDT\n\n"

            "<b>Начните знакомство с проектом.</b>"
        ),
        parse_mode="HTML",
        reply_markup=keyboard
    )


@dp.callback_query_handler(lambda c: c.data == "pay1")
async def pay1(callback_query: types.CallbackQuery):

    pay_url = create_invoice(3, "WD Premium 1 month")

    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("💳 Оплатить", url=pay_url),
        InlineKeyboardButton("🔄 Проверить оплату", callback_data="after1"),
        InlineKeyboardButton("⬅ Назад", callback_data="premium")
    )

    await bot.send_message(
        callback_query.from_user.id,
        "💳 Оплатите и затем нажмите «Проверить оплату»",
        reply_markup=keyboard
    )


@dp.callback_query_handler(lambda c: c.data == "after1")
async def after1(callback_query: types.CallbackQuery):

    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("✅ Подтвердить оплату", callback_data="check_pay_1"),
        InlineKeyboardButton("⬅ Назад", callback_data="premium")
    )

    await bot.send_message(
        callback_query.from_user.id,
        "Подтверди оплату",
        reply_markup=keyboard
    )


# ===== SUB2 =====
@dp.callback_query_handler(lambda c: c.data == "sub2")
async def sub2(callback_query: types.CallbackQuery):

    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("💳 Перейти к оплате", callback_data="pay2"),
        InlineKeyboardButton("⬅ Назад", callback_data="premium")
    )

    photo = InputFile("2months.jpg")

    await bot.send_photo(
        callback_query.from_user.id,
        photo,
        caption=(
            "💎 <b>WD Premium — 2 месяца</b>\n\n"

            "Оптимальный выбор для тех, кто хочет больше контента и выгоды.\n\n"

            "Вы получите:\n"
            "🔒 полный доступ ко всему Premium\n"
            "🔥 откровенный контент без ограничений\n"
            "⚡ ранние публикации\n"
            "📖 бонусные материалы\n"
            "✨ 1 персональная история\n\n"

            "⏳ Доступ: 60 дней\n"
            "💳 Стоимость: 5 USDT\n\n"

            "💡 <i>Выгоднее, чем брать по одному месяцу.</i>"
        ),
        parse_mode="HTML",
        reply_markup=keyboard
    )


@dp.callback_query_handler(lambda c: c.data == "pay2")
async def pay2(callback_query: types.CallbackQuery):

    pay_url = create_invoice(5, "WD Premium 2 months")

    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("💳 Оплатить", url=pay_url),
        InlineKeyboardButton("🔄 Проверить оплату", callback_data="after2"),
        InlineKeyboardButton("⬅ Назад", callback_data="premium")
    )

    await bot.send_message(
        callback_query.from_user.id,
        "💳 Оплатите и затем нажмите «Проверить оплату»",
        reply_markup=keyboard
    )


@dp.callback_query_handler(lambda c: c.data == "after2")
async def after2(callback_query: types.CallbackQuery):

    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("✅ Подтвердить оплату", callback_data="check_pay_2"),
        InlineKeyboardButton("⬅ Назад", callback_data="premium")
    )

    await bot.send_message(
        callback_query.from_user.id,
        "Подтверди оплату",
        reply_markup=keyboard
    )


# ===== SUB3 =====
@dp.callback_query_handler(lambda c: c.data == "sub3")
async def sub3(callback_query: types.CallbackQuery):

    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("💳 Перейти к оплате", callback_data="pay3"),
        InlineKeyboardButton("⬅ Назад", callback_data="premium")
    )

    photo = InputFile("3months.jpg")

    await bot.send_photo(
        callback_query.from_user.id,
        photo,
        caption=(
            "💎 <b>WD Premium — 3 месяца</b>\n\n"

            "Максимальный доступ и лучший вариант для постоянных участников.\n\n"

            "Вы получите:\n"
            "🔒 полный архив и весь Premium-контент\n"
            "🔥 самый откровенный формат проекта\n"
            "⚡ ранний доступ ко всем новинкам\n"
            "📖 бонусные сцены и истории\n"
            "✨ 3 персональные истории\n\n"

            "⏳ Доступ: 90 дней\n"
            "💳 Стоимость: 7 USDT\n\n"

            "🔥 <b>Самый выгодный тариф</b>"
        ),
        parse_mode="HTML",
        reply_markup=keyboard
    )


@dp.callback_query_handler(lambda c: c.data == "pay3")
async def pay3(callback_query: types.CallbackQuery):

    pay_url = create_invoice(7, "WD Premium 3 months")

    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("💳 Оплатить", url=pay_url),
        InlineKeyboardButton("🔄 Проверить оплату", callback_data="after3"),
        InlineKeyboardButton("⬅ Назад", callback_data="premium")
    )

    await bot.send_message(
        callback_query.from_user.id,
        "💳 Оплатите и затем нажмите «Проверить оплату»",
        reply_markup=keyboard
    )


@dp.callback_query_handler(lambda c: c.data == "after3")
async def after3(callback_query: types.CallbackQuery):

    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("✅ Подтвердить оплату", callback_data="check_pay_3"),
        InlineKeyboardButton("⬅ Назад", callback_data="premium")
    )

    await bot.send_message(
        callback_query.from_user.id,
        "Подтверди оплату",
        reply_markup=keyboard
    )


# ===== ПРОВЕРКА =====
@dp.callback_query_handler(lambda c: c.data.startswith("check_pay"))
async def check_payment(callback_query: types.CallbackQuery):

    user = callback_query.from_user

    tariff = {
        "check_pay_1": "1 месяц",
        "check_pay_2": "2 месяца",
        "check_pay_3": "3 месяца"
    }.get(callback_query.data, "неизвестно")

    username = f"@{user.username}" if user.username else "без username"

    await bot.send_message(
        user.id,
        "💎 Запрос на активацию принят.\n\nДоступ будет выдан в ближайшее время."
    )

    await bot.send_message(
        ADMIN_ID,
        f"💰 Новый запрос\n\nТариф: {tariff}\nПользователь: {username}\nID: {user.id}"
    )


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)