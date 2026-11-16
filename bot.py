import os
import asyncio
import requests
import sqlite3
import hmac
import hashlib
from decimal import Decimal, InvalidOperation
from urllib.parse import quote
from datetime import datetime, timedelta
from uuid import uuid4

from aiohttp import web

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputFile
from aiogram.utils import executor

# ===== ТОКЕНЫ =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
CRYPTO_TOKEN = os.getenv("CRYPTO_TOKEN")
YOOMONEY_RECEIVER = os.getenv("YOOMONEY_RECEIVER")
YOOMONEY_NOTIFICATION_SECRET = os.getenv("YOOMONEY_NOTIFICATION_SECRET")
YOOMONEY_PUBLIC_URL = os.getenv("YOOMONEY_PUBLIC_URL", "").rstrip("/")
ADMIN_ID = 7733841337

# ===== ИНИЦИАЛИЗАЦИЯ =====
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# ===== БАЗА ДАННЫХ =====
conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS subscriptions (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    tariff TEXT,
    end_date TEXT,
    notified INTEGER DEFAULT 0
)
""")


conn.commit()

# Заказы Telegram Stars и защита от повторной обработки платежей
cursor.execute("""
CREATE TABLE IF NOT EXISTS star_orders (
    payload TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    tariff TEXT NOT NULL,
    days INTEGER NOT NULL,
    amount INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
)
""")

# Сохраняем ID сообщения со счётом, чтобы удалить его после успешной оплаты.
existing_columns = {
    row[1] for row in cursor.execute("PRAGMA table_info(star_orders)").fetchall()
}
if "invoice_chat_id" not in existing_columns:
    cursor.execute("ALTER TABLE star_orders ADD COLUMN invoice_chat_id INTEGER")
if "invoice_message_id" not in existing_columns:
    cursor.execute("ALTER TABLE star_orders ADD COLUMN invoice_message_id INTEGER")

cursor.execute("""
CREATE TABLE IF NOT EXISTS star_payments (
    charge_id TEXT PRIMARY KEY,
    payload TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    amount INTEGER NOT NULL,
    paid_at TEXT NOT NULL
)
""")
conn.commit()

# Заказы и платежи ЮMoney. Метка label связывает перевод с заказом.
cursor.execute("""
CREATE TABLE IF NOT EXISTS yoomoney_orders (
    label TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    tariff TEXT NOT NULL,
    days INTEGER NOT NULL,
    amount INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    access_granted INTEGER NOT NULL DEFAULT 0,
    delivered INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS yoomoney_payments (
    operation_id TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    amount_paid TEXT NOT NULL,
    credited_amount TEXT NOT NULL,
    paid_at TEXT NOT NULL
)
""")
conn.commit()

user_invoices = {}

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
        return result["result"]
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
        InlineKeyboardButton("👑 Моя подписка", callback_data="my_sub"),
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

    await callback_query.answer()
    await callback_query.message.delete()

    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("💎 1 месяц — 170 ₽ / 190 ⭐ / 3 USDT", callback_data="sub1"),
        InlineKeyboardButton("💎 2 месяца — 280 ₽ / 310 ⭐ / 5 USDT", callback_data="sub2"),
        InlineKeyboardButton("💎 3 месяца — 490 ₽ / 465 ⭐ / 7 USDT", callback_data="sub3"),
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
        "💳 Оплата: ₽ ЮMoney / ⭐ Telegram Stars / USDT\n\n"
        "⏳ Доступ ограничен.\n\n"
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

    await callback_query.answer()
    await callback_query.message.delete()

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

    await callback_query.answer()
    await callback_query.message.delete()

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

    await callback_query.answer()
    await callback_query.message.delete()

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

    await callback_query.answer()
    await callback_query.message.delete()

    await start(callback_query.message)


# ===== SUB1 =====
@dp.callback_query_handler(lambda c: c.data == "sub1")
async def sub1(callback_query: types.CallbackQuery):

    await callback_query.answer()
    await callback_query.message.delete()

    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("₽ Оплатить 170 ₽", callback_data="ym1"),
        InlineKeyboardButton("⭐ Оплатить 190 Stars", callback_data="stars1"),
        InlineKeyboardButton("💳 Оплатить 3 USDT", callback_data="pay1"),
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
            "🔒 полный архив и весь Premium-контент\n"
            "🔥 самый откровенный формат проекта\n"
            "⚡ ранний доступ ко всем новинкам\n"
            "📖 бонусные сцены и истории\n"
            "✨ 1 персональная история\n\n"
            "⏳ Доступ: 30 дней\n"
            "💳 Стоимость: 190 ⭐ / 3 USDT / 170 ₽\n\n"
            "<b>Начните знакомство с проектом.</b>"
        ),
        parse_mode="HTML",
        reply_markup=keyboard
    )


@dp.callback_query_handler(lambda c: c.data == "pay1")
async def pay1(callback_query: types.CallbackQuery):

    await callback_query.answer()
    await callback_query.message.delete()

    invoice = create_invoice(3, "WD Premium 1 month")
    if not invoice:
        await bot.send_message(callback_query.from_user.id, "Не удалось создать счёт CryptoBot. Попробуйте позже.")
        return

    pay_url = invoice["pay_url"]
    invoice_id = invoice["invoice_id"]

    user_invoices[callback_query.from_user.id] = {
        "invoice_id": invoice_id,
        "type": "subscription",
        "tariff": "1 месяц"
    }

    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("💳 Оплатить", url=pay_url),
        InlineKeyboardButton("🔄 Проверить оплату", callback_data="check_pay_1"),
        InlineKeyboardButton("⬅ Назад", callback_data="premium")
    )

    await bot.send_message(
        callback_query.from_user.id,
        "💳 Оплатите и затем нажмите «Проверить оплату»",
        reply_markup=keyboard
    )


# ===== SUB2 =====
@dp.callback_query_handler(lambda c: c.data == "sub2")
async def sub2(callback_query: types.CallbackQuery):

    await callback_query.answer()
    await callback_query.message.delete()

    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("₽ Оплатить 280 ₽", callback_data="ym2"),
        InlineKeyboardButton("⭐ Оплатить 310 Stars", callback_data="stars2"),
        InlineKeyboardButton("💳 Оплатить 5 USDT", callback_data="pay2"),
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
            "🔒 полный архив и весь Premium-контент\n"
            "🔥 самый откровенный формат проекта\n"
            "⚡ ранний доступ ко всем новинкам\n"
            "📖 бонусные сцены и истории\n"
            "✨ 2 персональные истории\n\n"
            "⏳ Доступ: 60 дней\n"
            "💳 Стоимость: 310 ⭐ / 5 USDT / 280 ₽\n\n"
            "💡 <i>Выгоднее, чем брать по одному месяцу.</i>"
        ),
        parse_mode="HTML",
        reply_markup=keyboard
    )


@dp.callback_query_handler(lambda c: c.data == "pay2")
async def pay2(callback_query: types.CallbackQuery):

    await callback_query.answer()
    await callback_query.message.delete()

    invoice = create_invoice(5, "WD Premium 2 months")
    if not invoice:
        await bot.send_message(callback_query.from_user.id, "Не удалось создать счёт CryptoBot. Попробуйте позже.")
        return

    pay_url = invoice["pay_url"]
    invoice_id = invoice["invoice_id"]

    user_invoices[callback_query.from_user.id] = {
        "invoice_id": invoice_id,
        "type": "subscription",
        "tariff": "2 месяца"
    }

    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("💳 Оплатить", url=pay_url),
        InlineKeyboardButton("🔄 Проверить оплату", callback_data="check_pay_2"),
        InlineKeyboardButton("⬅ Назад", callback_data="premium")
    )

    await bot.send_message(
        callback_query.from_user.id,
        "💳 Оплатите и затем нажмите «Проверить оплату»",
        reply_markup=keyboard
    )


# ===== SUB3 =====
@dp.callback_query_handler(lambda c: c.data == "sub3")
async def sub3(callback_query: types.CallbackQuery):

    await callback_query.answer()
    await callback_query.message.delete()

    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("₽ Оплатить 490 ₽", callback_data="ym3"),
        InlineKeyboardButton("⭐ Оплатить 465 Stars", callback_data="stars3"),
        InlineKeyboardButton("💳 Оплатить 7 USDT", callback_data="pay3"),
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
            "✨ 3 персональная истории\n\n"
            "⏳ Доступ: 90 дней\n"
            "💳 Стоимость: 465 ⭐ / 7 USDT / 490 ₽\n\n"
            "🔥 <b>Самый выгодный тариф</b>"
        ),
        parse_mode="HTML",
        reply_markup=keyboard
    )


@dp.callback_query_handler(lambda c: c.data == "pay3")
async def pay3(callback_query: types.CallbackQuery):

    await callback_query.answer()
    await callback_query.message.delete()

    invoice = create_invoice(7, "WD Premium 3 months")
    if not invoice:
        await bot.send_message(callback_query.from_user.id, "Не удалось создать счёт CryptoBot. Попробуйте позже.")
        return

    pay_url = invoice["pay_url"]
    invoice_id = invoice["invoice_id"]

    user_invoices[callback_query.from_user.id] = {
        "invoice_id": invoice_id,
        "type": "subscription",
        "tariff": "3 месяца"
    }

    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("💳 Оплатить", url=pay_url),
        InlineKeyboardButton("🔄 Проверить оплату", callback_data="check_pay_3"),
        InlineKeyboardButton("⬅ Назад", callback_data="premium")
    )

    await bot.send_message(
        callback_query.from_user.id,
        "💳 Оплатите и затем нажмите «Проверить оплату»",
        reply_markup=keyboard
    )


# ===== ЮMONEY =====
YOOMONEY_TARIFFS = {
    "ym1": {"tariff": "1 месяц", "days": 30, "amount": 170},
    "ym2": {"tariff": "2 месяца", "days": 60, "amount": 280},
    "ym3": {"tariff": "3 месяца", "days": 90, "amount": 490},
}


@dp.callback_query_handler(lambda c: c.data in YOOMONEY_TARIFFS)
async def yoomoney_payment_start(callback_query: types.CallbackQuery):
    await callback_query.answer()

    if not YOOMONEY_RECEIVER or not YOOMONEY_PUBLIC_URL:
        await bot.send_message(
            callback_query.from_user.id,
            "Оплата через ЮMoney пока настраивается. Пожалуйста, выберите другой способ или попробуйте позже."
        )
        return

    plan = YOOMONEY_TARIFFS[callback_query.data]
    label = f"WD{callback_query.from_user.id}{uuid4().hex[:20]}"
    cursor.execute(
        """INSERT INTO yoomoney_orders
           (label, user_id, tariff, days, amount, status, created_at)
           VALUES (?, ?, ?, ?, ?, 'pending', ?)""",
        (
            label,
            callback_query.from_user.id,
            plan["tariff"],
            plan["days"],
            plan["amount"],
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    )
    conn.commit()

    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(
            f"₽ Перейти к оплате — {plan['amount']} ₽",
            url=f"{YOOMONEY_PUBLIC_URL}/yoomoney/pay/{label}"
        )
    )
    keyboard.add(InlineKeyboardButton("⬅ Назад", callback_data="premium"))

    await bot.send_message(
        callback_query.from_user.id,
        f"<b>✦ WD PREMIUM ✦</b>\n"
        f"<i>Оплата через ЮMoney</i>\n\n"
        f"Тариф: <b>{plan['tariff']}</b>\n"
        f"Сумма: <b>{plan['amount']} ₽</b>\n\n"
        "Нажмите кнопку ниже, выберите способ оплаты и подтвердите перевод.\n"
        "Доступ будет выдан автоматически после подтверждения платежа.",
        parse_mode="HTML",
        reply_markup=keyboard
    )


def yoomoney_signature_is_valid(data):
    if not YOOMONEY_NOTIFICATION_SECRET:
        return False

    received_sign = data.get("sign", "")
    if not received_sign:
        return False

    # ЮMoney требует RFC 3986-кодирование значений и сортировку ключей.
    canonical = "&".join(
        f"{key}={quote(str(data[key]), safe='-_.~')}"
        for key in sorted(data.keys())
        if key != "sign"
    )
    calculated = hmac.new(
        YOOMONEY_NOTIFICATION_SECRET.encode("utf-8"),
        canonical.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(calculated.lower(), received_sign.lower())


async def deliver_yoomoney_access(label):
    cursor.execute(
        """SELECT user_id, tariff, delivered
           FROM yoomoney_orders WHERE label = ? AND status = 'paid'""",
        (label,)
    )
    order = cursor.fetchone()
    if not order or order[2]:
        return True

    user_id, tariff, delivered = order
    try:
        cursor.execute(
            "SELECT end_date FROM subscriptions WHERE user_id = ?",
            (user_id,)
        )
        existing = cursor.fetchone()

        cursor.execute(
            "SELECT days FROM yoomoney_orders WHERE label = ?",
            (label,)
        )
        days = cursor.fetchone()[0]

        if existing:
            current_end = datetime.strptime(existing[0], "%Y-%m-%d %H:%M:%S")
            end_date = (
                current_end + timedelta(days=days)
                if current_end > datetime.now()
                else datetime.now() + timedelta(days=days)
            )
        else:
            end_date = datetime.now() + timedelta(days=days)

        # Защита от повторного продления: access_granted устанавливается один раз.
        cursor.execute(
            "SELECT access_granted FROM yoomoney_orders WHERE label = ?",
            (label,)
        )
        access_granted = cursor.fetchone()[0]

        if not access_granted:
            cursor.execute(
                "REPLACE INTO subscriptions VALUES (?, ?, ?, ?, ?)",
                (
                    user_id,
                    None,
                    tariff,
                    end_date.strftime("%Y-%m-%d %H:%M:%S"),
                    0
                )
            )
            cursor.execute(
                "UPDATE yoomoney_orders SET access_granted = 1 WHERE label = ?",
                (label,)
            )
            conn.commit()
        else:
            cursor.execute(
                "SELECT end_date FROM subscriptions WHERE user_id = ?",
                (user_id,)
            )
            saved = cursor.fetchone()
            if saved:
                end_date = datetime.strptime(saved[0], "%Y-%m-%d %H:%M:%S")

        invite = await bot.create_chat_invite_link(
            chat_id=-1003888233811,
            member_limit=1
        )
        await bot.send_message(
            user_id,
            "💎 <b>Оплата через ЮMoney прошла успешно!</b>\n\n"
            f"Тариф: {tariff}\n"
            f"Доступ действует до: {end_date.strftime('%d.%m.%Y %H:%M')}\n\n"
            f"Ваша ссылка для входа:\n{invite.invite_link}",
            parse_mode="HTML"
        )
        cursor.execute(
            "UPDATE yoomoney_orders SET delivered = 1 WHERE label = ?",
            (label,)
        )
        conn.commit()
        return True
    except Exception as exc:
        print(f"YooMoney delivery error for {label}: {exc}")
        return False


async def yoomoney_payment_page(request):
    label = request.match_info["label"]
    cursor.execute(
        "SELECT amount, status FROM yoomoney_orders WHERE label = ?",
        (label,)
    )
    order = cursor.fetchone()

    if not order or order[1] != "pending":
        return web.Response(
            text="Ссылка на оплату недействительна или заказ уже оплачен.",
            content_type="text/plain",
            status=404
        )

    if not YOOMONEY_RECEIVER:
        return web.Response(text="Оплата временно недоступна.", status=503)

    amount = int(order[0])
    # Сумма и метка берутся из базы, а не из параметров браузера.
    html = f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>WD Premium — оплата</title>
<style>
body{{font-family:Arial,sans-serif;background:#100d18;color:#f7f2ff;display:flex;
justify-content:center;align-items:center;min-height:100vh;margin:0}}
main{{width:min(420px,88vw);background:#211a2d;padding:28px;border-radius:18px;
box-sizing:border-box;text-align:center}}
h1{{letter-spacing:2px;font-size:22px}} p{{color:#d8cde5;line-height:1.5}}
label{{display:block;text-align:left;padding:12px;margin:10px 0;background:#30253f;border-radius:10px}}
button{{width:100%;padding:14px;border:0;border-radius:10px;background:#b78be8;
color:#170f20;font-weight:bold;font-size:16px;margin-top:12px}}
</style></head>
<body><main>
<h1>✦ WD PREMIUM ✦</h1>
<p>К оплате: <b>{amount} ₽</b></p>
<form method="POST" action="https://yoomoney.ru/quickpay/confirm">
<input type="hidden" name="receiver" value="{YOOMONEY_RECEIVER}">
<input type="hidden" name="quickpay-form" value="button">
<input type="hidden" name="sum" value="{amount}">
<input type="hidden" name="label" value="{label}">
<label><input type="radio" name="paymentType" value="PC" checked> Кошелёк ЮMoney</label>
<label><input type="radio" name="paymentType" value="AC"> Банковская карта</label>
<button type="submit">Перейти к оплате</button>
</form>
<p>После подтверждения перевода бот автоматически отправит ссылку для входа.</p>
</main></body></html>"""
    return web.Response(text=html, content_type="text/html")


async def yoomoney_notification(request):
    try:
        form = await request.post()
        data = {key: str(value) for key, value in form.items()}

        # Тестовые уведомления ЮMoney могут быть пустыми — просто подтверждаем доставку.
        if data.get("test_notification", "").lower() == "true":
            return web.Response(text="OK", status=200)

        if not yoomoney_signature_is_valid(data):
            print("YooMoney: invalid notification signature")
            return web.Response(text="Invalid signature", status=403)

        if (
            data.get("notification_type") not in ("p2p-incoming", "card-incoming")
            or data.get("currency") != "643"
            or data.get("unaccepted", "false").lower() != "false"
        ):
            return web.Response(text="Ignored", status=200)

        label = data.get("label", "")
        operation_id = data.get("operation_id", "")
        if not label or not operation_id:
            return web.Response(text="Missing payment identifiers", status=400)

        cursor.execute(
            """SELECT user_id, tariff, days, amount, status
               FROM yoomoney_orders WHERE label = ?""",
            (label,)
        )
        order = cursor.fetchone()
        if not order:
            return web.Response(text="Unknown order", status=200)

        user_id, tariff, days, expected_amount, status = order

        try:
            paid_amount = Decimal(data.get("withdraw_amount", "")).quantize(Decimal("0.01"))
        except (InvalidOperation, ValueError):
            return web.Response(text="Invalid amount", status=400)

        # withdraw_amount — сумма, списанная у покупателя; amount — зачисление
        # после комиссии ЮMoney, поэтому сравниваем именно withdraw_amount.
        if paid_amount != Decimal(expected_amount).quantize(Decimal("0.01")):
            print(f"YooMoney amount mismatch for {label}: {paid_amount}")
            return web.Response(text="Amount mismatch", status=400)

        cursor.execute(
            "SELECT label FROM yoomoney_payments WHERE operation_id = ?",
            (operation_id,)
        )
        duplicate = cursor.fetchone()

        if not duplicate:
            if status != "pending":
                return web.Response(text="Order already processed", status=200)

            cursor.execute(
                """INSERT INTO yoomoney_payments
                   (operation_id, label, user_id, amount_paid, credited_amount, paid_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    operation_id,
                    label,
                    user_id,
                    str(paid_amount),
                    data.get("amount", ""),
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
            )
            cursor.execute(
                "UPDATE yoomoney_orders SET status = 'paid' WHERE label = ?",
                (label,)
            )
            conn.commit()

        delivered = await deliver_yoomoney_access(label)
        if not delivered:
            return web.Response(text="Delivery pending; retry later", status=500)

        return web.Response(text="OK", status=200)

    except Exception as exc:
        print(f"YooMoney notification error: {exc}")
        return web.Response(text="Server error", status=500)


async def start_web_server(dispatcher):
    app = web.Application()
    app.router.add_get("/yoomoney/pay/{label}", yoomoney_payment_page)
    app.router.add_post("/yoomoney/notify", yoomoney_notification)

    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", "8080"))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"YooMoney HTTP server listening on port {port}")


async def on_startup(dispatcher):
    asyncio.create_task(subscription_checker())
    await start_web_server(dispatcher)


# ===== ПРОВЕРКА =====
@dp.callback_query_handler(lambda c: c.data.startswith("check_pay"))
async def check_payment(callback_query: types.CallbackQuery):

    await callback_query.answer()
    await callback_query.message.delete()

    user_id = callback_query.from_user.id

    if user_id not in user_invoices:
        keyboard = InlineKeyboardMarkup()

        keyboard.add(
            InlineKeyboardButton(
                "💎 Купить подписку",
                callback_data="premium"
            )
        )

        keyboard.add(
            InlineKeyboardButton(
                "⬅ Назад",
                callback_data="back"
            )
        )

        await bot.send_message(
            user_id,
            "❌ Счёт не найден. Попробуйте создать новый.",
            reply_markup=keyboard
        )
        return

    invoice_data = user_invoices[user_id]
    invoice_id = invoice_data["invoice_id"]

    url = "https://pay.crypt.bot/api/getInvoices"

    headers = {
        "Crypto-Pay-API-Token": CRYPTO_TOKEN
    }

    params = {
        "invoice_ids": invoice_id
    }

    response = requests.get(
        url,
        headers=headers,
        params=params
    )

    result = response.json()

    if not result["ok"]:

        keyboard = InlineKeyboardMarkup()

        keyboard.add(
            InlineKeyboardButton(
                "🔄 Проверить оплату",
                callback_data="check_payment"
            )
        )

        keyboard.add(
            InlineKeyboardButton(
                "⬅ Назад",
                callback_data="back"
            )
        )

        await bot.send_message(
            user_id,
            "⚠️ Не удалось проверить оплату.\n\n"
            "Попробуйте ещё раз через несколько секунд.",
            reply_markup=keyboard
        )

        return

    items = result["result"]["items"]

    if not items:

        keyboard = InlineKeyboardMarkup()

        keyboard.add(
            InlineKeyboardButton(
                "🔄 Проверить оплату",
                callback_data="check_payment"
            )
        )

        keyboard.add(
            InlineKeyboardButton(
                "⬅ Назад",
                callback_data="back"
            )
        )

        await bot.send_message(
            user_id,
            "❌ Счёт не найден.\n\n"
            "Попробуйте создать новый счёт.",
            reply_markup=keyboard
        )

        return

    invoice = items[0]

    if invoice["status"] != "paid":

        keyboard = InlineKeyboardMarkup()

        keyboard.add(
            InlineKeyboardButton(
                "🔄 Проверить оплату",
                callback_data="check_payment"
            )
        )

        keyboard.add(
            InlineKeyboardButton(
                "⬅ Назад",
                callback_data="back"
            )
        )

        await bot.send_message(
            user_id,
            "❌ Оплата не найдена.\n\n"
            "Если вы уже оплатили — подождите несколько секунд "
            "и попробуйте проверить оплату ещё раз.",
            reply_markup=keyboard
        )

        return

    # ===== ОПЛАТА УСПЕШНА =====

    tariff = invoice_data["tariff"]

    if tariff == "1 месяц":
        days = 30

    elif tariff == "2 месяца":
        days = 60

    else:
        days = 90

    # ===== ПРОВЕРЯЕМ СУЩЕСТВУЮЩУЮ ПОДПИСКУ =====

    cursor.execute(
        "SELECT end_date FROM subscriptions WHERE user_id = ?",
        (user_id,)
    )

    existing = cursor.fetchone()

    if existing:

        current_end = datetime.strptime(
            existing[0],
            "%Y-%m-%d %H:%M:%S"
        )

        if current_end > datetime.now():
            end_date = current_end + timedelta(days=days)

        else:
            end_date = datetime.now() + timedelta(days=days)

    else:
        end_date = datetime.now() + timedelta(days=days)

    # ===== СОХРАНЯЕМ В БАЗУ =====

    cursor.execute(
        "REPLACE INTO subscriptions VALUES (?, ?, ?, ?, ?)",
        (
            user_id,
            callback_query.from_user.username,
            tariff,
            end_date.strftime("%Y-%m-%d %H:%M:%S"),
            0
        )
    )

    conn.commit()

    # ===== СОЗДАЁМ ССЫЛКУ В КАНАЛ =====

    invite = await bot.create_chat_invite_link(
        chat_id=-1003888233811,
        member_limit=1
    )

    invite_link = invite.invite_link

    await bot.send_message(
        user_id,
        f"💎 Оплата прошла успешно!\n\n"
        f"Вот ваш доступ:\n{invite_link}"
    )

    del user_invoices[user_id]


# ===== TELEGRAM STARS =====

STAR_TARIFFS = {
    "stars1": {"tariff": "1 месяц", "days": 30, "amount": 190},
    "stars2": {"tariff": "2 месяца", "days": 60, "amount": 310},
    "stars3": {"tariff": "3 месяца", "days": 90, "amount": 465},
}


async def create_stars_invoice(callback_query: types.CallbackQuery, plan_key: str):
    plan = STAR_TARIFFS[plan_key]
    user_id = callback_query.from_user.id

    # Уникальный payload связывает конкретный счёт с пользователем и тарифом
    payload = f"wd:{user_id}:{plan_key}:{uuid4().hex[:12]}"

    cursor.execute(
        """INSERT INTO star_orders (payload, user_id, tariff, days, amount, status)
           VALUES (?, ?, ?, ?, ?, 'pending')""",
        (payload, user_id, plan["tariff"], plan["days"], plan["amount"])
    )
    conn.commit()

    invoice_message = await bot.send_invoice(
        chat_id=user_id,
        title=f"WD Premium — {plan['tariff']}",
        description=f"Доступ к WD Premium на {plan['days']} дней",
        payload=payload,
        provider_token="",
        currency="XTR",
        prices=[
            types.LabeledPrice(
                label=f"WD Premium — {plan['tariff']}",
                amount=plan["amount"]
            )
        ]
    )

    cursor.execute(
        """UPDATE star_orders
           SET invoice_chat_id = ?, invoice_message_id = ?
           WHERE payload = ?""",
        (invoice_message.chat.id, invoice_message.message_id, payload)
    )
    conn.commit()


@dp.callback_query_handler(lambda c: c.data in STAR_TARIFFS)
async def stars_payment_start(callback_query: types.CallbackQuery):
    await callback_query.answer()

    plan = STAR_TARIFFS[callback_query.data]
    await callback_query.message.delete()

    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton(
            "⭐ Оплатить",
            callback_data=f"stars_pay:{callback_query.data}"
        ),
        InlineKeyboardButton(
            "⬅ Назад",
            callback_data="premium"
        )
    )

    await bot.send_message(
        callback_query.from_user.id,
        f"<b>✦ WD PREMIUM ✦</b>\n"
        f"<i>PRIVATE MEMBERS CLUB</i>\n\n"
        f"<b>{plan['amount']} ⭐</b>\n"
        f"<b>ДОСТУП НА {plan['days']} ДНЕЙ</b>\n\n"
        f"Эксклюзивные истории, закрытый архив и особенный контент WD Premium.\n"
        f"<i>Ваше личное пространство начинается здесь.</i>",
        parse_mode="HTML",
        reply_markup=keyboard
    )


@dp.callback_query_handler(lambda c: c.data.startswith("stars_pay:"))
async def stars_payment_invoice(callback_query: types.CallbackQuery):
    await callback_query.answer()
    plan_key = callback_query.data.split(":", 1)[1]

    if plan_key not in STAR_TARIFFS:
        return

    await callback_query.message.delete()
    await create_stars_invoice(callback_query, plan_key)


@dp.pre_checkout_query_handler(lambda query: True)
async def process_pre_checkout_query(pre_checkout_query: types.PreCheckoutQuery):
    cursor.execute(
        """SELECT user_id, amount, status
           FROM star_orders WHERE payload = ?""",
        (pre_checkout_query.invoice_payload,)
    )
    order = cursor.fetchone()

    if (
        order
        and order[0] == pre_checkout_query.from_user.id
        and order[1] == pre_checkout_query.total_amount
        and pre_checkout_query.currency == "XTR"
        and order[2] == "pending"
    ):
        await bot.answer_pre_checkout_query(
            pre_checkout_query.id,
            ok=True
        )
    else:
        await bot.answer_pre_checkout_query(
            pre_checkout_query.id,
            ok=False,
            error_message="Счёт недействителен или уже обработан. Создайте новый."
        )


@dp.message_handler(content_types=types.ContentType.SUCCESSFUL_PAYMENT)
async def process_successful_payment(message: types.Message):
    payment = message.successful_payment
    payload = payment.invoice_payload
    user_id = message.from_user.id

    cursor.execute(
        """SELECT tariff, days, amount, status, user_id,
                  invoice_chat_id, invoice_message_id
           FROM star_orders WHERE payload = ?""",
        (payload,)
    )
    order = cursor.fetchone()

    if not order:
        await message.answer(
            "Платёж получен, но заказ не найден. Напишите менеджеру WD: @Ki1iWD"
        )
        return

    (
        tariff, days, expected_amount, status, order_user_id,
        invoice_chat_id, invoice_message_id
    ) = order

    if (
        payment.currency != "XTR"
        or payment.total_amount != expected_amount
        or order_user_id != user_id
    ):
        await message.answer(
            "Не удалось автоматически сверить платёж. Напишите менеджеру WD: @Ki1iWD"
        )
        return

    # Повторное обновление подписки по одному и тому же платежу запрещено
    cursor.execute(
        "SELECT 1 FROM star_payments WHERE charge_id = ?",
        (payment.telegram_payment_charge_id,)
    )
    if cursor.fetchone():
        await message.answer("Этот платёж уже был обработан.")
        return

    if status != "pending":
        await message.answer("Этот заказ уже обработан.")
        return

    cursor.execute(
        """INSERT INTO star_payments
           (charge_id, payload, user_id, amount, paid_at)
           VALUES (?, ?, ?, ?, ?)""",
        (
            payment.telegram_payment_charge_id,
            payload,
            user_id,
            payment.total_amount,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    )
    cursor.execute(
        "UPDATE star_orders SET status = 'paid' WHERE payload = ?",
        (payload,)
    )
    conn.commit()

    # Удаляем сообщение со Stars-счётом после подтверждённой оплаты.
    if invoice_chat_id and invoice_message_id:
        try:
            await bot.delete_message(invoice_chat_id, invoice_message_id)
        except Exception:
            # Ошибка удаления не должна мешать выдаче оплаченного доступа.
            pass

    # Продлеваем текущую подписку или создаём новую
    cursor.execute(
        "SELECT end_date FROM subscriptions WHERE user_id = ?",
        (user_id,)
    )
    existing = cursor.fetchone()

    if existing:
        current_end = datetime.strptime(existing[0], "%Y-%m-%d %H:%M:%S")
        if current_end > datetime.now():
            end_date = current_end + timedelta(days=days)
        else:
            end_date = datetime.now() + timedelta(days=days)
    else:
        end_date = datetime.now() + timedelta(days=days)

    cursor.execute(
        "REPLACE INTO subscriptions VALUES (?, ?, ?, ?, ?)",
        (
            user_id,
            message.from_user.username,
            tariff,
            end_date.strftime("%Y-%m-%d %H:%M:%S"),
            0
        )
    )
    conn.commit()

    # Создаём персональную ссылку на один вход
    invite = await bot.create_chat_invite_link(
        chat_id=-1003888233811,
        member_limit=1
    )

    await message.answer(
        "⭐ <b>Оплата Telegram Stars прошла успешно!</b>\n\n"
        f"Тариф: {tariff}\n"
        f"Доступ действует до: {end_date.strftime('%d.%m.%Y %H:%M')}\n\n"
        f"Ваша ссылка для входа:\n{invite.invite_link}",
        parse_mode="HTML"
    )


# ===== ПРОВЕРКА ПОДПИСОК =====
async def subscription_checker():

    while True:

        cursor.execute(
            "SELECT user_id, end_date, notified FROM subscriptions"
        )

        subscriptions = cursor.fetchall()

        now = datetime.now()

        for sub in subscriptions:

            user_id = sub[0]

            end_date = datetime.strptime(
                sub[1],
                "%Y-%m-%d %H:%M:%S"
            )

            notified = sub[2]

            remaining = end_date - now

            # ===== НАПОМИНАНИЕ =====

            if remaining > timedelta(0) and remaining <= timedelta(days=3) and notified == 0:

                try:

                    keyboard = InlineKeyboardMarkup()

                    keyboard.add(
                        InlineKeyboardButton(
                            "💎 Продлить подписку",
                            callback_data="premium"
                        )
                    )

                    keyboard.add(
                        InlineKeyboardButton(
                            "⬅ Назад",
                            callback_data="back"
                        )
                    )

                    await bot.send_message(
                        user_id,
                        "⏳ Ваша подписка скоро закончится.\n\n"
                        "Продлите доступ заранее.",
                        reply_markup=keyboard
                    )

                    cursor.execute(
                        "UPDATE subscriptions SET notified = 1 WHERE user_id = ?",
                        (user_id,)
                    )

                    conn.commit()

                except:
                    pass

            # ===== ЕСЛИ ПОДПИСКА КОНЧИЛАСЬ =====

            if now >= end_date:

                try:

                    await bot.ban_chat_member(
                        chat_id=-1003888233811,
                        user_id=user_id
                    )

                    await bot.unban_chat_member(
                        chat_id=-1003888233811,
                        user_id=user_id
                    )

                    await bot.send_message(
                        user_id,
                        "❌ Ваша подписка закончилась."
                    )

                except:
                    pass

                cursor.execute(
                    "DELETE FROM subscriptions WHERE user_id = ?",
                    (user_id,)
                )

                conn.commit()

        await asyncio.sleep(3600)



@dp.message_handler(commands=["paysupport"])
async def payment_support(message: types.Message):
    await message.answer(
        "По вопросам оплаты WD Premium напишите менеджеру: @Ki1iWD"
    )


@dp.message_handler(commands=["terms"])
async def terms(message: types.Message):
    await message.answer(
        "Условия WD Premium: после подтверждения оплаты доступ предоставляется "
        "на выбранный срок. По вопросам доступа, возврата или спорных платежей "
        "напишите менеджеру WD: @Ki1iWD"
    )


@dp.message_handler(commands=["subscribe"])
async def subscribe_info(message: types.Message):

    cursor.execute(
        "SELECT tariff, end_date FROM subscriptions WHERE user_id = ?",
        (message.from_user.id,)
    )

    sub = cursor.fetchone()

    if not sub:

        await message.answer(
            "❌ У вас нет активной подписки."
        )

        return

    tariff = sub[0]

    end_date = datetime.strptime(
        sub[1],
        "%Y-%m-%d %H:%M:%S"
    )

    remaining = (end_date - datetime.now()).days

    await message.answer(
        f"💎 WD Premium\n\n"
        f"Тариф: {tariff}\n\n"
        f"Действует до:\n"
        f"{sub[1]}\n\n"
        f"Осталось дней: {remaining}"
    )


@dp.callback_query_handler(lambda c: c.data == "my_sub")
async def my_subscription(callback_query: types.CallbackQuery):

    await callback_query.answer()
    await callback_query.message.delete()

    cursor.execute(
        "SELECT tariff, end_date FROM subscriptions WHERE user_id = ?",
        (callback_query.from_user.id,)
    )

    sub = cursor.fetchone()

    if not sub:

        keyboard = InlineKeyboardMarkup()

        keyboard.add(
            InlineKeyboardButton(
                "💎 Купить подписку",
                callback_data="premium"
            )
        )

        keyboard.add(
            InlineKeyboardButton(
                "⬅ Назад",
                callback_data="back"
            )
        )

        await bot.send_message(
            callback_query.from_user.id,
            "❌ У вас нет активной подписки.",
            reply_markup=keyboard
        )

        return

    tariff = sub[0]

    end_date = datetime.strptime(
        sub[1],
        "%Y-%m-%d %H:%M:%S"
    )

    remaining = (end_date - datetime.now()).days

    keyboard = InlineKeyboardMarkup()

    keyboard.add(
        InlineKeyboardButton(
            "💎 Продлить подписку",
            callback_data="premium"
        )
    )

    keyboard.add(
        InlineKeyboardButton(
            "⬅ Назад",
            callback_data="back"
        )
    )

    await bot.send_message(
        callback_query.from_user.id,
        f"👑 <b>WD Premium</b>\n\n"
        f"📦 Тариф: {tariff}\n\n"
        f"📅 Активна до:\n"
        f"{sub[1]}\n\n"
        f"⏳ Осталось дней: {remaining}",
        parse_mode="HTML",
        reply_markup=keyboard
    )


@dp.channel_post_handler()
async def get_channel_id(message: types.Message):
    print(message.chat.id)


async def resilient_polling():
    """
    Получает обновления Telegram и переживает временные сетевые ошибки
    (например, HTTP 502 Bad Gateway), не завершая работу всего приложения.
    """
    offset = None

    while True:
        try:
            updates = await bot.get_updates(
                offset=offset,
                timeout=30
            )

            if updates:
                # Сразу продвигаем offset, чтобы Telegram не присылал
                # уже полученные обновления повторно.
                offset = updates[-1].update_id + 1
                await dp.process_updates(updates)

        except asyncio.CancelledError:
            raise
        except Exception as exc:
            print(f"Telegram polling error: {type(exc).__name__}: {exc}")
            print("Повторное подключение к Telegram через 5 секунд...")
            await asyncio.sleep(5)


async def main():
    print("BOT STARTING...")
    await on_startup(dp)

    try:
        await resilient_polling()
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())