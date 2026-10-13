import asyncio
import logging
import sqlite3
import random
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup,
    InlineKeyboardButton, CallbackQuery, LabeledPrice, PreCheckoutQuery
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

BOT_TOKEN = "8786182073:AAHbIx7OLcHmBYBwkZ5PSSKBvrdVVFQwHIk"
ADMIN_ID = 1695344206

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

conn = sqlite3.connect("school.db")
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id INTEGER UNIQUE,
    nickname TEXT UNIQUE,
    balance INTEGER DEFAULT 0,
    koch INTEGER DEFAULT 0,
    frozen INTEGER DEFAULT 0,
    rating REAL DEFAULT 0,
    is_executor INTEGER DEFAULT 0,
    is_banned INTEGER DEFAULT 0,
    last_bonus TEXT,
    last_nick_change TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
cur.execute("""
CREATE TABLE IF NOT EXISTS executors (
    account_id INTEGER PRIMARY KEY,
    subjects TEXT, grade TEXT, price INTEGER, about TEXT
)
""")
cur.execute("""
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER, executor_id INTEGER,
    title TEXT, description TEXT, deadline TEXT, price INTEGER,
    photo_file_id TEXT, solution_file_id TEXT,
    status TEXT DEFAULT 'open',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
cur.execute("""
CREATE TABLE IF NOT EXISTS services (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    author_id INTEGER,
    title TEXT, description TEXT,
    category TEXT, price INTEGER,
    currency TEXT DEFAULT 'gold',
    photo_file_id TEXT,
    promoted INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
cur.execute("""
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER, type TEXT, amount INTEGER,
    balance_after INTEGER, related_order_id INTEGER,
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
cur.execute("""
CREATE TABLE IF NOT EXISTS news (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    author_id INTEGER, title TEXT, text TEXT,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
cur.execute("""
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER, author_id INTEGER, executor_id INTEGER,
    rating INTEGER, text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
cur.execute("""
CREATE TABLE IF NOT EXISTS disputes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER, author_id INTEGER, reason TEXT,
    status TEXT DEFAULT 'open',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
cur.execute("""
CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER, sender_id INTEGER, receiver_id INTEGER,
    message_type TEXT, content TEXT, file_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
cur.execute("""
CREATE TABLE IF NOT EXISTS forum (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    author_id INTEGER, question TEXT, answer TEXT,
    answer_author_id INTEGER,
    status TEXT DEFAULT 'open',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
cur.execute("""
CREATE TABLE IF NOT EXISTS withdraw_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER, gold_amount INTEGER, stars_amount INTEGER,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()

def safe_alter(sql):
    try:
        cur.execute(sql); conn.commit()
    except: pass

safe_alter("ALTER TABLE orders ADD COLUMN title TEXT")
safe_alter("ALTER TABLE orders ADD COLUMN description TEXT")
safe_alter("ALTER TABLE orders ADD COLUMN photo_file_id TEXT")
safe_alter("ALTER TABLE orders ADD COLUMN solution_file_id TEXT")
safe_alter("ALTER TABLE accounts ADD COLUMN last_bonus TEXT")
safe_alter("ALTER TABLE accounts ADD COLUMN last_nick_change TEXT")
safe_alter("ALTER TABLE services ADD COLUMN currency TEXT DEFAULT 'gold'")
safe_alter("ALTER TABLE services ADD COLUMN promoted INTEGER DEFAULT 0")


main_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="💰 Баланс")],
    [KeyboardButton(text="📦 Заказы"), KeyboardButton(text="🏪 Услуги")],
    [KeyboardButton(text="🥔 Коч-Магазин"), KeyboardButton(text="🎰 Слоты")],
    [KeyboardButton(text="🎁 Бонус"), KeyboardButton(text="🎁 Подарить")],
    [KeyboardButton(text="📰 Новости"), KeyboardButton(text="💬 Форум")],
    [KeyboardButton(text="🛠 Стать исполнителем"), KeyboardButton(text="❓ Помощь")]
], resize_keyboard=True)

orders_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="➕ Создать заказ"), KeyboardButton(text="📋 Все заказы")],
    [KeyboardButton(text="📥 Мои заказы")],
    [KeyboardButton(text="🔙 Назад")]
], resize_keyboard=True)

services_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="➕ Создать анкету"), KeyboardButton(text="🏪 Все анкеты")],
    [KeyboardButton(text="📁 Мои анкеты")],
    [KeyboardButton(text="🔙 Назад")]
], resize_keyboard=True)

koch_shop_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="➕ Создать коч-анкету"), KeyboardButton(text="🥔 Все коч-анкеты")],
    [KeyboardButton(text="📁 Мои коч-анкеты")],
    [KeyboardButton(text="🔙 Назад")]
], resize_keyboard=True)

forum_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="❓ Задать вопрос"), KeyboardButton(text="📖 Все вопросы")],
    [KeyboardButton(text="🔙 Назад")]
], resize_keyboard=True)

balance_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="⭐ Пополнить голду", callback_data="topup_start")],
    [InlineKeyboardButton(text="💸 Обменять голду на звёзды", callback_data="withdraw_start")],
    [InlineKeyboardButton(text="📜 История транзакций", callback_data="history")]
])

cancel_kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)

skip_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="➡️ Пропустить")],
    [KeyboardButton(text="❌ Отмена")]
], resize_keyboard=True)

class Reg(StatesGroup):
    waiting_nickname = State()

class ChangeNick(StatesGroup):
    new_nick = State()

class ExecutorForm(StatesGroup):
    subjects = State(); grade = State(); price = State(); about = State()

class OrderForm(StatesGroup):
    title = State(); description = State(); deadline = State(); price = State(); photo = State()

class ServiceForm(StatesGroup):
    title = State(); description = State(); category = State(); price = State(); currency = State(); photo = State()

class TopupForm(StatesGroup):
    amount = State()

class WithdrawForm(StatesGroup):
    amount = State()

class NewsForm(StatesGroup):
    title = State(); text = State()

class ReviewForm(StatesGroup):
    rating = State(); text = State()

class DisputeForm(StatesGroup):
    reason = State()

class ChatForm(StatesGroup):
    message = State()

class ForumForm(StatesGroup):
    question = State(); answer = State()

class GiftForm(StatesGroup):
    recipient = State(); amount = State()

def get_account(tg_id):
    cur.execute("SELECT * FROM accounts WHERE tg_id = ?", (tg_id,))
    return cur.fetchone()

def get_account_by_id(acc_id):
    cur.execute("SELECT * FROM accounts WHERE id = ?", (acc_id,))
    return cur.fetchone()

def get_account_by_nick(nick):
    cur.execute("SELECT * FROM accounts WHERE nickname = ?", (nick,))
    return cur.fetchone()

def create_account(tg_id, nickname):
    cur.execute("INSERT INTO accounts (tg_id, nickname) VALUES (?, ?)", (tg_id, nickname))
    conn.commit()

def nickname_taken(nickname):
    cur.execute("SELECT 1 FROM accounts WHERE nickname = ?", (nickname,))
    return cur.fetchone() is not None

def get_executor(account_id):
    cur.execute("SELECT * FROM executors WHERE account_id = ?", (account_id,))
    return cur.fetchone()

def save_executor(account_id, subjects, grade, price, about):
    cur.execute("INSERT OR REPLACE INTO executors (account_id, subjects, grade, price, about) VALUES (?, ?, ?, ?, ?)",
                (account_id, subjects, grade, price, about))
    cur.execute("UPDATE accounts SET is_executor = 1 WHERE id = ?", (account_id,))
    conn.commit()

def log_tx(account_id, tx_type, amount, related_order_id=None, comment=None):
    cur.execute("SELECT balance FROM accounts WHERE id = ?", (account_id,))
    balance = cur.fetchone()[0]
    cur.execute("""INSERT INTO transactions (account_id, type, amount, balance_after, related_order_id, comment)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (account_id, tx_type, amount, balance, related_order_id, comment))
    conn.commit()

def add_gold(account_id, amount, comment="Начисление"):
    cur.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, account_id))
    conn.commit()
    log_tx(account_id, "gold_in", amount, None, comment)

def add_koch(account_id, amount, comment="Начисление коч-коинов"):
    cur.execute("UPDATE accounts SET koch = koch + ? WHERE id = ?", (amount, account_id))
    conn.commit()

def freeze_balance(account_id, amount, order_id):
    cur.execute("UPDATE accounts SET balance = balance - ?, frozen = frozen + ? WHERE id = ?", (amount, amount, account_id))
    conn.commit()
    log_tx(account_id, "freeze", -amount, order_id, "Заморозка под заказ")

def unfreeze_to_executor(customer_id, executor_id, amount, order_id):
    commission = int(amount * 0.15)
    to_executor = amount - commission
    cur.execute("UPDATE accounts SET frozen = frozen - ? WHERE id = ?", (amount, customer_id))
    cur.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (to_executor, executor_id))
    conn.commit()
    log_tx(customer_id, "unfreeze", 0, order_id, "Заказ выполнен")
    log_tx(executor_id, "payout", to_executor, order_id, f"Оплата заказа (комиссия {commission})")

def unfreeze_to_customer(customer_id, amount, order_id, comment="Возврат"):
    cur.execute("UPDATE accounts SET frozen = frozen - ?, balance = balance + ? WHERE id = ?", (amount, amount, customer_id))
    conn.commit()
    log_tx(customer_id, "refund", amount, order_id, comment)

def create_order(customer_id, title, description, deadline, price, photo=None):
    cur.execute("INSERT INTO orders (customer_id, title, description, deadline, price, photo_file_id) VALUES (?, ?, ?, ?, ?, ?)",
                (customer_id, title, description, deadline, price, photo))
    conn.commit()
    return cur.lastrowid

def get_open_orders():
    cur.execute("SELECT * FROM orders WHERE status = 'open' ORDER BY id DESC LIMIT 20")
    return cur.fetchall()

def get_order(order_id):
    cur.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
    return cur.fetchone()

def create_service(author_id, title, description, category, price, currency, photo=None):
    cur.execute("INSERT INTO services (author_id, title, description, category, price, currency, photo_file_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (author_id, title, description, category, price, currency, photo))
    conn.commit()
    return cur.lastrowid

def get_services(currency='gold'):
    cur.execute("SELECT * FROM services WHERE status = 'active' AND currency = ? ORDER BY promoted DESC, id DESC LIMIT 30", (currency,))
    return cur.fetchall()

def get_my_services(author_id, currency=None):
    if currency:
        cur.execute("SELECT * FROM services WHERE author_id = ? AND status = 'active' AND currency = ? ORDER BY id DESC", (author_id, currency))
    else:
        cur.execute("SELECT * FROM services WHERE author_id = ? AND status = 'active' ORDER BY id DESC", (author_id,))
    return cur.fetchall()

def get_service(service_id):
    cur.execute("SELECT * FROM services WHERE id = ?", (service_id,))
    return cur.fetchone()

def create_news(author_id, title, text):
    cur.execute("INSERT INTO news (author_id, title, text) VALUES (?, ?, ?)", (author_id, title, text))
    conn.commit()
    return cur.lastrowid

def get_news():
    cur.execute("SELECT * FROM news WHERE status = 'active' ORDER BY id DESC LIMIT 20")
    return cur.fetchall()

def is_admin(tg_id):
    return tg_id == ADMIN_ID

def add_review(order_id, author_id, executor_id, rating, text):
    cur.execute("INSERT INTO reviews (order_id, author_id, executor_id, rating, text) VALUES (?, ?, ?, ?, ?)",
                (order_id, author_id, executor_id, rating, text))
    conn.commit()
    cur.execute("SELECT AVG(rating) FROM reviews WHERE executor_id = ?", (executor_id,))
    avg = cur.fetchone()[0] or 0
    cur.execute("UPDATE accounts SET rating = ? WHERE id = ?", (round(avg, 1), executor_id))
    conn.commit()

def get_reviews(executor_id):
    cur.execute("SELECT * FROM reviews WHERE executor_id = ? ORDER BY id DESC LIMIT 10", (executor_id,))
    return cur.fetchall()

def create_dispute(order_id, author_id, reason):
    cur.execute("INSERT INTO disputes (order_id, author_id, reason) VALUES (?, ?, ?)", (order_id, author_id, reason))
    conn.commit()
    return cur.lastrowid

def save_chat_message(order_id, sender_id, receiver_id, message_type, content, file_id=None):
    cur.execute("""INSERT INTO chat_messages (order_id, sender_id, receiver_id, message_type, content, file_id)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (order_id, sender_id, receiver_id, message_type, content, file_id))
    conn.commit()

def get_chat_history(order_id):
    cur.execute("SELECT * FROM chat_messages WHERE order_id = ? ORDER BY id ASC", (order_id,))
    return cur.fetchall()

def create_forum_question(author_id, question):
    cur.execute("INSERT INTO forum (author_id, question) VALUES (?, ?)", (author_id, question))
    conn.commit()
    return cur.lastrowid

def get_forum_questions():
    cur.execute("SELECT * FROM forum ORDER BY id DESC LIMIT 30")
    return cur.fetchall()

def get_forum_question(qid):
    cur.execute("SELECT * FROM forum WHERE id = ?", (qid,))
    return cur.fetchone()

def answer_forum(qid, author_id, answer):
    cur.execute("UPDATE forum SET answer = ?, answer_author_id = ?, status = 'answered' WHERE id = ?",
                (answer, author_id, qid))
    conn.commit()

def create_withdraw(account_id, gold_amount, stars_amount):
    cur.execute("INSERT INTO withdraw_requests (account_id, gold_amount, stars_amount) VALUES (?, ?, ?)",
                (account_id, gold_amount, stars_amount))
    conn.commit()
    return cur.lastrowid

def get_public_stats():
    cur.execute("SELECT COUNT(*) FROM accounts"); users = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM orders"); orders = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM orders WHERE status = 'done'"); done = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM services WHERE status = 'active'"); services = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM news WHERE status = 'active'"); news = cur.fetchone()[0]
    cur.execute("SELECT nickname, rating FROM accounts WHERE is_executor = 1 ORDER BY rating DESC LIMIT 3")
    top = cur.fetchall()
    return users, orders, done, services, news, top

def transfer_gold(from_id, to_id, amount):
    cur.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount, from_id))
    cur.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (amount, to_id))
    conn.commit()
    log_tx(from_id, "gift_out", -amount, None, f"Подарок юзеру #{to_id}")
    log_tx(to_id, "gift_in", amount, None, f"Подарок от юзера #{from_id}")

def transfer_koch(from_id, to_id, amount):
    cur.execute("UPDATE accounts SET koch = koch - ? WHERE id = ?", (amount, from_id))
    cur.execute("UPDATE accounts SET koch = koch + ? WHERE id = ?", (amount, to_id))
    conn.commit()

@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    try: await message.delete()
    except: pass
    acc = get_account(message.from_user.id)
    if acc:
        if acc[8]:
            await message.answer("🚫 Ты забанен.")
            return
        await message.answer(f"С возвращением, {acc[2]}! 🔥\n💰 {acc[3]} голды | 🥔 {acc[4]} коч-коинов", reply_markup=main_kb)
        return
    await message.answer("Привет! 🔥\nЯ бот «Горелый Питушок».\n\nПридумай ник:")
    await state.set_state(Reg.waiting_nickname)

@dp.message(Reg.waiting_nickname, F.text)
async def process_nickname(message: Message, state: FSMContext):
    nickname = message.text.strip()
    try: await message.delete()
    except: pass
    if len(nickname) < 3 or len(nickname) > 20:
        await message.answer("Ник от 3 до 20 символов. Ещё раз:")
        return
    if nickname_taken(nickname):
        await message.answer("Ник занят. Другой:")
        return
    create_account(message.from_user.id, nickname)
    await state.clear()
    await message.answer(
        f"✅ Аккаунт создан!\nНик: {nickname}\n💰 0 голды | 🥔 0 коч-коинов",
        reply_markup=main_kb
    )

@dp.message(F.text == "👤 Профиль")
async def btn_profile(message: Message):
    try: await message.delete()
    except: pass
    acc = get_account(message.from_user.id)
    if not acc:
        await message.answer("Сначала /start"); return
    text = (f"👤 Ник: {acc[2]}\n"
            f"💰 Голда: {acc[3]}\n"
            f"🥔 Коч-Коины: {acc[4]}\n"
            f"❄️ Заморожено: {acc[5]}\n"
            f"⭐ Рейтинг: {acc[6]}\n"
            f"🛠 Исполнитель: {'да' if acc[7] else 'нет'}")
    if acc[7]:
        ex = get_executor(acc[0])
        if ex:
            text += f"\n\n📚 {ex[1]}\n🎓 {ex[2]}\n💵 {ex[3]} голды\n📝 {ex[4]}"
        reviews = get_reviews(acc[0])
        if reviews:
            text += f"\n\n📝 Отзывы:"
            for r in reviews[:3]:
                author = get_account_by_id(r[2])
                text += f"\n⭐ {r[4]}/5 от {author[2] if author else '?'}: {r[5][:50]}"
    await message.answer(text)

@dp.message(F.text == "💰 Баланс")
async def btn_balance(message: Message):
    try: await message.delete()
    except: pass
    acc = get_account(message.from_user.id)
    if not acc:
        await message.answer("Сначала /start"); return
    await message.answer(
        f"💰 Голда: {acc[3]}\n🥔 Коч-Коины: {acc[4]}\n❄️ Заморожено: {acc[5]}\n\n"
        f"Курс: 1 Star = 1 голда (комиссия 10%)\n"
        f"⚠️ Коч-Коины нельзя купить или вывести.",
        reply_markup=balance_kb
    )

@dp.callback_query(F.data == "topup_start")
async def topup_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "Введи сколько голды хочешь купить (от 1 до 1000).\n"
        "1 Star = 1 голда, но с комиссией 10% (получишь 90% от суммы).\n\n"
        "Пример: платишь 100 ⭐ → получаешь 90 💰",
        reply_markup=cancel_kb
    )
    await state.set_state(TopupForm.amount)
    await callback.answer()

@dp.message(TopupForm.amount, F.text)
async def topup_amount(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_kb)
        return
    if not message.text.isdigit():
        await message.answer("Нужно число. Ещё раз:")
        return
    amount = int(message.text)
    if amount < 1 or amount > 1000:
        await message.answer("От 1 до 1000. Ещё раз:")
        return
    await state.clear()
    try: await message.delete()
    except: pass
    await bot.send_invoice(
        chat_id=message.from_user.id,
        title=f"{amount} Stars",
        description=f"Оплата {amount} ⭐, получишь {int(amount * 0.9)} голды",
        payload=f"topup_{amount}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=f"{amount} Stars", amount=amount)]
    )

@dp.pre_checkout_query()
async def pre_checkout(pre_checkout_q: PreCheckoutQuery):
    await pre_checkout_q.answer(ok=True)

@dp.message(F.successful_payment)
async def successful_payment(message: Message):
    payload = message.successful_payment.invoice_payload
    stars = message.successful_payment.total_amount
    acc = get_account(message.from_user.id)
    if not acc:
        return
    amount_paid = int(payload.replace("topup_", ""))
    commission = int(amount_paid * 0.10)
    golda = amount_paid - commission
    add_gold(acc[0], golda, f"Пополнение {stars} ⭐ (комиссия {commission})")
    await message.answer(
        f"✅ Оплачено {stars} ⭐\n"
        f"Комиссия (10%): {commission} ⭐\n"
        f"Зачислено: {golda} 💰\n"
        f"Баланс: {acc[3] + golda} голды",
        reply_markup=main_kb
    )

@dp.callback_query(F.data == "withdraw_start")
async def withdraw_start(callback: CallbackQuery, state: FSMContext):
    acc = get_account(callback.from_user.id)
    if not acc:
        await callback.answer("Сначала /start", show_alert=True); return
    await callback.message.answer(
        f"💸 Обмен голды на звёзды\n\n"
        f"У тебя: {acc[3]} 💰\n\n"
        f"Курс: 1 голда = 1 ⭐\n"
        f"Введи сколько голды хочешь обменять (мин. 10):\n\n"
        f"⚠️ Заявка рассматривается администрацией вручную.",
        reply_markup=cancel_kb
    )
    await state.set_state(WithdrawForm.amount)
    await callback.answer()

@dp.message(WithdrawForm.amount, F.text)
async def withdraw_amount(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_kb)
        return
    if not message.text.isdigit():
        await message.answer("Нужно число. Ещё раз:")
        return
    amount = int(message.text)
    acc = get_account(message.from_user.id)
    if amount < 10:
        await message.answer("Минимум 10 голды. Ещё раз:")
        return
    if amount > acc[3]:
        await message.answer(f"У тебя только {acc[3]} голды. Ещё раз:")
        return
    cur.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (amount, acc[0]))
    conn.commit()
    log_tx(acc[0], "withdraw_request", -amount, None, f"Заявка на обмен {amount} 💰 → {amount} ⭐")
    req_id = create_withdraw(acc[0], amount, amount)
    try: await message.delete()
    except: pass
    await state.clear()
    await message.answer(
        f"⏳ Анкета рассматривается\n\n"
        f"Заявка #{req_id} создана.\n"
        f"Списано: {amount} 💰\n"
        f"К получению: {amount} ⭐\n\n"
        f"Администрация рассмотрит и отправит звёзды.",
        reply_markup=main_kb
    )
    try:
        await bot.send_message(
            ADMIN_ID,
            f"💸 Заявка на вывод #{req_id}\n"
            f"Юзер: {acc[2]}\n"
            f"Голда: {amount} 💰\n"
            f"Звёзды: {amount} ⭐\n\n"
            f"/approve_withdraw {req_id}\n/reject_withdraw {req_id}"
        )
    except: pass

@dp.callback_query(F.data == "history")
async def show_history(callback: CallbackQuery):
    acc = get_account(callback.from_user.id)
    if not acc:
        await callback.answer("Сначала /start", show_alert=True); return
    cur.execute("SELECT type, amount, comment, created_at FROM transactions WHERE account_id = ? ORDER BY id DESC LIMIT 10", (acc[0],))
    txs = cur.fetchall()
    if not txs:
        await callback.answer("Транзакций нет.", show_alert=True); return
    text = "📜 Последние 10 транзакций:\n\n"
    for t in txs:
        sign = "+" if t[1] > 0 else ""
        text += f"{sign}{t[1]} 💰 — {t[2]} ({t[3][:16]})\n"
    await callback.message.answer(text)
    await callback.answer()

@dp.message(Command("changename"))
async def changename_start(message: Message, state: FSMContext):
    try: await message.delete()
    except: pass
    acc = get_account(message.from_user.id)
    if not acc:
        await message.answer("Сначала /start"); return
    last = acc[10]
    now = datetime.now()
    if last:
        try:
            last_dt = datetime.fromisoformat(last)
            if now - last_dt < timedelta(days=7):
                remains = timedelta(days=7) - (now - last_dt)
                days = remains.days
                hours = remains.seconds // 3600
                await message.answer(f"⏳ Ник можно менять раз в 7 дней.\nОсталось: {days}д {hours}ч")
                return
        except: pass
    await message.answer(f"✏️ Текущий ник: {acc[2]}\n\nВведи новый ник (3-20 символов):", reply_markup=cancel_kb)
    await state.set_state(ChangeNick.new_nick)

@dp.message(ChangeNick.new_nick, F.text)
async def changename_process(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_kb)
        return
    new_nick = message.text.strip()
    if len(new_nick) < 3 or len(new_nick) > 20:
        await message.answer("Ник от 3 до 20 символов. Ещё раз:")
        return
    if nickname_taken(new_nick):
        await message.answer("Ник занят. Другой:")
        return
    acc = get_account(message.from_user.id)
    old_nick = acc[2]
    now = datetime.now().isoformat()
    cur.execute("UPDATE accounts SET nickname = ?, last_nick_change = ? WHERE id = ?", (new_nick, now, acc[0]))
    conn.commit()
    try: await message.delete()
    except: pass
    await state.clear()
    await message.answer(f"✅ Ник изменён!\nБыло: {old_nick}\nСтало: {new_nick}\n\nСледующая смена через 7 дней.", reply_markup=main_kb)

@dp.message(F.text == "🎁 Бонус")
async def daily_bonus(message: Message):
    try: await message.delete()
    except: pass
    acc = get_account(message.from_user.id)
    if not acc:
        await message.answer("Сначала /start"); return
    last = acc[9]
    now = datetime.now()
    if last:
        try:
            last_dt = datetime.fromisoformat(last)
            if now - last_dt < timedelta(hours=24):
                remains = timedelta(hours=24) - (now - last_dt)
                hours = remains.seconds // 3600
                minutes = (remains.seconds % 3600) // 60
                await message.answer(f"⏳ Бонус уже получен. Следующий через {hours}ч {minutes}м.")
                return
        except: pass
    add_koch(acc[0], 10, "Ежедневный бонус")
    cur.execute("UPDATE accounts SET last_bonus = ? WHERE id = ?", (now.isoformat(), acc[0]))
    conn.commit()
    await message.answer(f"🎁 Бонус получен!\n+10 🥔\nТеперь у тебя: {acc[4] + 10} коч-коинов.")

@dp.message(F.text == "🎁 Подарить")
async def gift_start(message: Message, state: FSMContext):
    try: await message.delete()
    except: pass
    acc = get_account(message.from_user.id)
    if not acc:
        await message.answer("Сначала /start"); return
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="💰 Голда"), KeyboardButton(text="🥔 Коч-Коины")],
        [KeyboardButton(text="❌ Отмена")]
    ], resize_keyboard=True)
    await message.answer("Что подарить?", reply_markup=kb)
    await state.set_state(GiftForm.recipient)

@dp.message(GiftForm.recipient, F.text)
async def gift_type(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_kb)
        return
    if message.text not in ["💰 Голда", "🥔 Коч-Коины"]:
        await message.answer("Выбери кнопкой."); return
    currency = "gold" if message.text == "💰 Голда" else "koch"
    await state.update_data(gift_currency=currency)
    try: await message.delete()
    except: pass
    await message.answer("Введи ник получателя:", reply_markup=cancel_kb)

@dp.message(GiftForm.amount, F.text)
async def gift_recipient(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_kb)
        return
    recipient_nick = message.text.strip()
    recipient = get_account_by_nick(recipient_nick)
    sender = get_account(message.from_user.id)
    if not recipient:
        await message.answer("Нет такого юзера. Ещё раз:")
        return
    if recipient[0] == sender[0]:
        await message.answer("Нельзя подарить себе. Ещё раз:")
        return
    await state.update_data(gift_recipient_id=recipient[0], gift_recipient_nick=recipient[2])
    try: await message.delete()
    except: pass
    data = await state.get_data()
    if data["gift_currency"] == "gold":
        await message.answer(f"Сколько 💰 подарить {recipient[2]}? (у тебя {sender[3]})")
    else:
        await message.answer(f"Сколько 🥔 подарить {recipient[2]}? (у тебя {sender[4]})")

@dp.message(GiftForm.amount, F.text)
async def gift_amount(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_kb)
        return
    if not message.text.isdigit():
        await message.answer("Число. Ещё раз:")
        return
    amount = int(message.text)
    if amount < 1:
        await message.answer("Минимум 1. Ещё раз:")
        return
    data = await state.get_data()
    sender = get_account(message.from_user.id)
    if data["gift_currency"] == "gold":
        if sender[3] < amount:
            await message.answer(f"У тебя только {sender[3]} 💰")
            return
        transfer_gold(sender[0], data["gift_recipient_id"], amount)
        await message.answer(f"✅ Подарено {amount} 💰 юзеру {data['gift_recipient_nick']}")
    else:
        if sender[4] < amount:
            await message.answer(f"У тебя только {sender[4]} 🥔")
            return
        transfer_koch(sender[0], data["gift_recipient_id"], amount)
        await message.answer(f"✅ Подарено {amount} 🥔 юзеру {data['gift_recipient_nick']}")
    try: await message.delete()
    except: pass
    await state.clear()
    recipient = get_account_by_id(data["gift_recipient_id"])
    if recipient:
        try:
            emoji = "💰" if data["gift_currency"] == "gold" else "🥔"
            await bot.send_message(recipient[1], f"🎁 Тебе подарок от {sender[2]}!\n+{amount} {emoji}")
        except: pass
    await message.answer("Готово!", reply_markup=main_kb)


@dp.message(F.text == "🎰 Слоты")
async def slots_menu(message: Message):
    try: await message.delete()
    except: pass
    acc = get_account(message.from_user.id)
    if not acc:
        await message.answer("Сначала /start"); return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎰 Крутить (5 коч-коинов)", callback_data="spin")]
    ])
    await message.answer(
        f"🎰 Слоты\n\nСпин: 5 🥔\nУ тебя: {acc[4]} 🥔\n\n"
        f"🍎🍎🍎 = 10 🥔\n🍇🍇🍇 = 25 🥔\n7️⃣7️⃣7️⃣ = 100 🥔\nДве одинаковые = 3 🥔\n\n"
        f"⚠️ Голда не выпадает.",
        reply_markup=kb
    )

@dp.callback_query(F.data == "spin")
async def spin_slot(callback: CallbackQuery):
    acc = get_account(callback.from_user.id)
    if not acc:
        await callback.answer("Сначала /start", show_alert=True); return
    if acc[4] < 5:
        await callback.answer("Недостаточно коч-коинов. Нужно 5.", show_alert=True); return
    add_koch(acc[0], -5, "Спин в слотах")
    symbols = ["🍎", "🍇", "7️⃣"]
    reel = [random.choice(symbols) for _ in range(3)]
    result_text = " | ".join(reel)
    win = 0
    if reel[0] == reel[1] == reel[2]:
        if reel[0] == "7️⃣": win = 100
        elif reel[0] == "🍇": win = 25
        elif reel[0] == "🍎": win = 10
    elif reel[0] == reel[1] or reel[1] == reel[2] or reel[0] == reel[2]:
        win = 3
    if win > 0:
        add_koch(acc[0], win, f"Выигрыш ({result_text})")
    new_acc = get_account(callback.from_user.id)
    text = f"🎰 {result_text}\n\n"
    if win > 0:
        text += f"🎉 Выигрыш: +{win} 🥔\n"
    else:
        text += f"😢 Не повезло.\n"
    text += f"\nБаланс: {new_acc[4]} 🥔"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎰 Крутить ещё (5 🥔)", callback_data="spin")]
    ])
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except:
        await callback.message.answer(text, reply_markup=kb)
    await callback.answer()

@dp.message(F.text == "📰 Новости")
async def btn_news(message: Message):
    try: await message.delete()
    except: pass
    news = get_news()
    if not news:
        await message.answer("📰 Новостей пока нет."); return
    for n in news:
        text = f"📰 #{n[0]}\n📌 {n[2]}\n\n{n[3]}\n\n🕒 {n[5][:16]}"
        await message.answer(text)

@dp.message(F.text == "💬 Форум")
async def btn_forum(message: Message):
    try: await message.delete()
    except: pass
    await message.answer("💬 Форум вопросов:", reply_markup=forum_kb)

@dp.message(F.text == "❓ Задать вопрос")
async def forum_ask_start(message: Message, state: FSMContext):
    try: await message.delete()
    except: pass
    acc = get_account(message.from_user.id)
    if not acc:
        await message.answer("Сначала /start"); return
    await message.answer("❓ Напиши свой вопрос:", reply_markup=cancel_kb)
    await state.set_state(ForumForm.question)

@dp.message(ForumForm.question, F.text)
async def forum_question(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_kb)
        return
    acc = get_account(message.from_user.id)
    qid = create_forum_question(acc[0], message.text)
    try: await message.delete()
    except: pass
    await state.clear()
    await message.answer(f"✅ Вопрос #{qid} опубликован!", reply_markup=main_kb)

@dp.message(F.text == "📖 Все вопросы")
async def forum_list(message: Message):
    try: await message.delete()
    except: pass
    questions = get_forum_questions()
    if not questions:
        await message.answer("Вопросов нет."); return
    for q in questions:
        author = get_account_by_id(q[1])
        text = f"❓ #{q[0]}\n👤 {author[2] if author else '?'}\n\n{q[2]}"
        if q[3]:
            ans_author = get_account_by_id(q[4])
            text += f"\n\n✅ Ответ от {ans_author[2] if ans_author else '?'}:\n{q[3]}"
            await message.answer(text)
        else:
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💬 Ответить", callback_data=f"ans_{q[0]}")]
            ])
            await message.answer(text, reply_markup=kb)

@dp.callback_query(F.data.startswith("ans_"))
async def forum_answer_start(callback: CallbackQuery, state: FSMContext):
    qid = int(callback.data.split("_")[1])
    await state.update_data(forum_qid=qid)
    await callback.message.answer("💬 Напиши ответ:", reply_markup=cancel_kb)
    await state.set_state(ForumForm.answer)
    await callback.answer()

@dp.message(ForumForm.answer, F.text)
async def forum_answer(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_kb)
        return
    data = await state.get_data()
    qid = data.get("forum_qid")
    acc = get_account(message.from_user.id)
    q = get_forum_question(qid)
    if not q:
        await state.clear()
        await message.answer("Вопрос не найден.", reply_markup=main_kb)
        return
    answer_forum(qid, acc[0], message.text)
    try: await message.delete()
    except: pass
    await state.clear()
    await message.answer("✅ Ответ опубликован!", reply_markup=main_kb)
    question_author = get_account_by_id(q[1])
    if question_author and question_author[1] != message.from_user.id:
        try:
            await bot.send_message(question_author[1], f"💬 На твой вопрос #{qid} ответили!\n\nОтвет от {acc[2]}: {message.text}")
        except: pass

@dp.message(F.text == "🛠 Стать исполнителем")
async def btn_executor(message: Message, state: FSMContext):
    try: await message.delete()
    except: pass
    acc = get_account(message.from_user.id)
    if not acc:
        await message.answer("Сначала /start"); return
    ex = get_executor(acc[0])
    if ex:
        await message.answer(f"Анкета:\n📚 {ex[1]}\n🎓 {ex[2]}\n💵 {ex[3]}\n📝 {ex[4]}\n\nНапиши «Заново» чтобы перезаполнить.", reply_markup=cancel_kb)
        return
    await message.answer("Шаг 1/4: Предметы?", reply_markup=cancel_kb)
    await state.set_state(ExecutorForm.subjects)

@dp.message(F.text == "Заново")
async def restart_executor(message: Message, state: FSMContext):
    try: await message.delete()
    except: pass
    await message.answer("Шаг 1/4: Предметы?", reply_markup=cancel_kb)
    await state.set_state(ExecutorForm.subjects)

@dp.message(F.text == "❌ Отмена")
async def cancel_any(message: Message, state: FSMContext):
    try: await message.delete()
    except: pass
    await state.clear()
    await message.answer("Отменено.", reply_markup=main_kb)

@dp.message(F.text == "🔙 Назад")
async def back_main(message: Message, state: FSMContext):
    try: await message.delete()
    except: pass
    await state.clear()
    await message.answer("Главное меню.", reply_markup=main_kb)

@dp.message(ExecutorForm.subjects, F.text)
async def ex_subjects(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_kb)
        return
    await state.update_data(subjects=message.text)
    try: await message.delete()
    except: pass
    await message.answer("Шаг 2/4: Класс?")
    await state.set_state(ExecutorForm.grade)

@dp.message(ExecutorForm.grade, F.text)
async def ex_grade(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_kb)
        return
    await state.update_data(grade=message.text)
    try: await message.delete()
    except: pass
    await message.answer("Шаг 3/4: Средняя цена (голда)?")
    await state.set_state(ExecutorForm.price)

@dp.message(ExecutorForm.price, F.text)
async def ex_price(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_kb)
        return
    if not message.text.isdigit():
        await message.answer("Число. Ещё:"); return
    await state.update_data(price=int(message.text))
    try: await message.delete()
    except: pass
    await message.answer("Шаг 4/4: О себе?")
    await state.set_state(ExecutorForm.about)

@dp.message(ExecutorForm.about, F.text)
async def ex_about(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_kb)
        return
    data = await state.get_data()
    acc = get_account(message.from_user.id)
    save_executor(acc[0], data["subjects"], data["grade"], data["price"], message.text)
    try: await message.delete()
    except: pass
    await state.clear()
    await message.answer(f"✅ Анкета сохранена!\n📚 {data['subjects']}\n🎓 {data['grade']}\n💵 {data['price']}", reply_markup=main_kb)

@dp.message(F.text == "❓ Помощь")
async def btn_help(message: Message):
    try: await message.delete()
    except: pass
    await message.answer(
        "Кнопки:\n"
        "👤 Профиль\n💰 Баланс\n📦 Заказы\n🏪 Услуги\n🥔 Коч-Магазин\n🎰 Слоты\n"
        "🎁 Бонус\n🎁 Подарить\n📰 Новости\n💬 Форум\n🛠 Стать исполнителем\n❓ Помощь\n\n"
        "Команды:\n"
        "/changename — сменить ник (раз в 7 дней)\n"
        "/stats — статистика"
    )

@dp.message(Command("stats"))
async def public_stats(message: Message):
    try: await message.delete()
    except: pass
    if is_admin(message.from_user.id):
        await show_stats2(message)
        return
    users, orders, done, services, news, top = get_public_stats()
    text = (
        f"📊 Статистика платформы\n\n"
        f"👥 Юзеров: {users}\n"
        f"📦 Заказов: {orders} (✅ {done})\n"
        f"🏪 Услуг: {services}\n"
        f"📰 Новостей: {news}\n\n"
        f"🏆 Топ исполнителей:"
    )
    if top:
        for i, t in enumerate(top, 1):
            text += f"\n{i}. {t[0]} — ⭐ {t[1] or 0}"
    else:
        text += "\nПока нет"
    await message.answer(text)

@dp.message(F.text == "📦 Заказы")
async def btn_orders(message: Message):
    try: await message.delete()
    except: pass
    await message.answer("Раздел заказов:", reply_markup=orders_kb)

@dp.message(F.text == "➕ Создать заказ")
async def create_order_start(message: Message, state: FSMContext):
    try: await message.delete()
    except: pass
    acc = get_account(message.from_user.id)
    if not acc:
        await message.answer("Сначала /start"); return
    await message.answer("Шаг 1/5: Заголовок?", reply_markup=cancel_kb)
    await state.set_state(OrderForm.title)

@dp.message(OrderForm.title, F.text)
async def order_title(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_kb)
        return
    await state.update_data(title=message.text)
    try: await message.delete()
    except: pass
    await message.answer("Шаг 2/5: Описание.")
    await state.set_state(OrderForm.description)

@dp.message(OrderForm.description, F.text)
async def order_desc(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_kb)
        return
    await state.update_data(description=message.text)
    try: await message.delete()
    except: pass
    await message.answer("Шаг 3/5: Дедлайн?")
    await state.set_state(OrderForm.deadline)

@dp.message(OrderForm.deadline, F.text)
async def order_deadline(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_kb)
        return
    await state.update_data(deadline=message.text)
    try: await message.delete()
    except: pass
    await message.answer("Шаг 4/5: Цена в голде?")
    await state.set_state(OrderForm.price)

@dp.message(OrderForm.price, F.text)
async def order_price(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_kb)
        return
    if not message.text.isdigit():
        await message.answer("Число. Ещё:"); return
    price = int(message.text)
    acc = get_account(message.from_user.id)
    if acc[3] < price:
        await message.answer(f"❌ Мало голды. Нужно {price}, у тебя {acc[3]}.", reply_markup=main_kb)
        await state.clear()
        return
    await state.update_data(price=price)
    try: await message.delete()
    except: pass
    await message.answer("Шаг 5/5: Фото 📸 или «➡️ Пропустить»", reply_markup=skip_kb)
    await state.set_state(OrderForm.photo)

@dp.message(OrderForm.photo, F.photo)
async def order_photo(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    data = await state.get_data()
    acc = get_account(message.from_user.id)
    order_id = create_order(acc[0], data["title"], data["description"], data["deadline"], data["price"], photo_id)
    try: await message.delete()
    except: pass
    await state.clear()
    await message.answer(f"✅ Заказ #{order_id} создан!\n📌 {data['title']}\n💵 {data['price']} 💰", reply_markup=main_kb)

@dp.message(OrderForm.photo, F.text == "➡️ Пропустить")
async def order_skip_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    acc = get_account(message.from_user.id)
    order_id = create_order(acc[0], data["title"], data["description"], data["deadline"], data["price"])
    try: await message.delete()
    except: pass
    await state.clear()
    await message.answer(f"✅ Заказ #{order_id} создан!\n📌 {data['title']}\n💵 {data['price']} 💰", reply_markup=main_kb)

@dp.message(OrderForm.photo)
async def order_photo_wrong(message: Message):
    await message.answer("Пришли фото или нажми «➡️ Пропустить».")

@dp.message(F.text == "📋 Все заказы")
async def list_orders(message: Message):
    try: await message.delete()
    except: pass
    orders = get_open_orders()
    if not orders:
        await message.answer("Открытых заказов нет."); return
    for o in orders:
        customer = get_account_by_id(o[1])
        text = (f"📦 Заказ #{o[0]}\n👤 {customer[2] if customer else '?'}\n"
                f"📌 {o[3]}\n📝 {o[4]}\n⏰ {o[5]}\n💵 {o[6]} голды")
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✋ Взять", callback_data=f"take_{o[0]}")]
        ])
        if o[7]:
            await message.answer_photo(photo=o[7], caption=text, reply_markup=kb)
        else:
            await message.answer(text, reply_markup=kb)

@dp.message(F.text == "📥 Мои заказы")
async def my_orders(message: Message):
    try: await message.delete()
    except: pass
    acc = get_account(message.from_user.id)
    if not acc:
        await message.answer("Сначала /start"); return
    cur.execute("SELECT * FROM orders WHERE customer_id = ? OR executor_id = ? ORDER BY id DESC", (acc[0], acc[0]))
    orders = cur.fetchall()
    if not orders:
        await message.answer("У тебя нет заказов."); return
    for o in orders:
        role = "заказчик" if o[1] == acc[0] else "исполнитель"
        text = f"📦 #{o[0]} [{o[9]}] — {role}\n📌 {o[3]}\n💵 {o[6]} 💰"
        btns = []
        can_delete = (o[1] == acc[0]) or is_admin(message.from_user.id)
        if o[1] == acc[0] and o[9] == "taken":
            btns.append([InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_{o[0]}")])
            btns.append([InlineKeyboardButton(text="❌ Отменить", callback_data=f"cancel_{o[0]}")])
        if o[9] == "taken":
            btns.append([InlineKeyboardButton(text="💬 Чат", callback_data=f"chat_{o[0]}")])
            btns.append([InlineKeyboardButton(text="⚖️ Спор", callback_data=f"dispute_{o[0]}")])
        if o[1] == acc[0] and o[9] == "done":
            cur.execute("SELECT 1 FROM reviews WHERE order_id = ?", (o[0],))
            if not cur.fetchone():
                btns.append([InlineKeyboardButton(text="⭐ Отзыв", callback_data=f"review_{o[0]}")])
        if can_delete and o[9] in ("open", "cancelled", "done"):
            btns.append([InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delord_{o[0]}")])
        kb = InlineKeyboardMarkup(inline_keyboard=btns) if btns else None
        await message.answer(text, reply_markup=kb)

@dp.callback_query(F.data.startswith("take_"))
async def take_order_cb(callback: CallbackQuery):
    order_id = int(callback.data.split("_")[1])
    acc = get_account(callback.from_user.id)
    if not acc:
        await callback.answer("Сначала /start", show_alert=True); return
    if not acc[7]:
        await callback.answer("Сначала анкету!", show_alert=True); return
    order = get_order(order_id)
    if not order or order[9] != "open":
        await callback.answer("Уже взят.", show_alert=True); return
    if order[1] == acc[0]:
        await callback.answer("Это твой.", show_alert=True); return
    customer = get_account_by_id(order[1])
    if customer[3] < order[6]:
        await callback.answer("Мало голды.", show_alert=True); return
    freeze_balance(customer[0], order[6], order_id)
    cur.execute("UPDATE orders SET executor_id = ?, status = 'taken' WHERE id = ?", (acc[0], order_id))
    conn.commit()
    await callback.answer("Заказ твой!")
    try:
        await bot.send_message(customer[1], f"🎉 Заказ #{order_id} взял {acc[2]}!\n💰 {order[6]} заморожено.")
    except: pass

@dp.callback_query(F.data.startswith("confirm_"))
async def confirm_order_cb(callback: CallbackQuery):
    order_id = int(callback.data.split("_")[1])
    acc = get_account(callback.from_user.id)
    order = get_order(order_id)
    if not order or order[1] != acc[0]:
        await callback.answer("Не твой.", show_alert=True); return
    if order[9] != "taken":
        await callback.answer("Не «взят».", show_alert=True); return
    unfreeze_to_executor(order[1], order[2], order[6], order_id)
    cur.execute("UPDATE orders SET status = 'done' WHERE id = ?", (order_id,))
    conn.commit()
    executor = get_account_by_id(order[2])
    if executor:
        try:
            await bot.send_message(executor[1], f"✅ Заказ #{order_id} подтверждён! +{int(order[6]*0.85)} 💰")
        except: pass
    await callback.message.edit_text(callback.message.text + "\n\n✅ Подтверждено.")
    await callback.answer("Готово!")

@dp.callback_query(F.data.startswith("cancel_"))
async def cancel_order_cb(callback: CallbackQuery):
    order_id = int(callback.data.split("_")[1])
    acc = get_account(callback.from_user.id)
    order = get_order(order_id)
    if not order or order[1] != acc[0]:
        await callback.answer("Не твой.", show_alert=True); return
    if order[9] == "taken":
        unfreeze_to_customer(order[1], order[6], order_id, "Возврат")
    cur.execute("UPDATE orders SET status = 'cancelled' WHERE id = ?", (order_id,))
    conn.commit()
    await callback.message.edit_text(callback.message.text + "\n\n❌ Отменён.")
    await callback.answer("Отменено.")

@dp.callback_query(F.data.startswith("delord_"))
async def delete_order_cb(callback: CallbackQuery):
    order_id = int(callback.data.split("_")[1])
    acc = get_account(callback.from_user.id)
    order = get_order(order_id)
    if not order:
        await callback.answer("Не найден.", show_alert=True); return
    if order[1] != acc[0] and not is_admin(callback.from_user.id):
        await callback.answer("Чужой.", show_alert=True); return
    if order[9] == "taken":
        await callback.answer("В работе.", show_alert=True); return
    cur.execute("DELETE FROM orders WHERE id = ?", (order_id,))
    conn.commit()
    await callback.message.edit_text(callback.message.text + "\n\n🗑 Удалён.")
    await callback.answer("Удалено.")

@dp.message(F.text == "🏪 Услуги")
async def btn_services(message: Message):
    try: await message.delete()
    except: pass
    await message.answer("🏪 Услуги за голду:", reply_markup=services_kb)

@dp.message(F.text == "➕ Создать анкету")
async def service_create_start(message: Message, state: FSMContext):
    try: await message.delete()
    except: pass
    acc = get_account(message.from_user.id)
    if not acc:
        await message.answer("Сначала /start"); return
    await state.update_data(service_currency='gold')
    await message.answer("Шаг 1/5: Заголовок?", reply_markup=cancel_kb)
    await state.set_state(ServiceForm.title)

@dp.message(ServiceForm.title, F.text)
async def service_title(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_kb)
        return
    await state.update_data(title=message.text)
    try: await message.delete()
    except: pass
    await message.answer("Шаг 2/5: Описание.")
    await state.set_state(ServiceForm.description)

@dp.message(ServiceForm.description, F.text)
async def service_desc(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_kb)
        return
    await state.update_data(description=message.text)
    try: await message.delete()
    except: pass
    await message.answer("Шаг 3/5: Категория?")
    await state.set_state(ServiceForm.category)

@dp.message(ServiceForm.category, F.text)
async def service_category(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_kb)
        return
    await state.update_data(category=message.text)
    try: await message.delete()
    except: pass
    await message.answer("Шаг 4/5: Цена?")
    await state.set_state(ServiceForm.price)

@dp.message(ServiceForm.price, F.text)
async def service_price(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_kb)
        return
    if not message.text.isdigit():
        await message.answer("Число. Ещё:"); return
    await state.update_data(price=int(message.text))
    try: await message.delete()
    except: pass
    await message.answer("Шаг 5/5: Фото 📸 или «➡️ Пропустить»", reply_markup=skip_kb)
    await state.set_state(ServiceForm.photo)

@dp.message(ServiceForm.photo, F.photo)
async def service_photo(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    data = await state.get_data()
    acc = get_account(message.from_user.id)
    currency = data.get("service_currency", "gold")
    sid = create_service(acc[0], data["title"], data["description"], data["category"], data["price"], currency, photo_id)
    try: await message.delete()
    except: pass
    await state.clear()
    emoji = "💰" if currency == "gold" else "🥔"
    await message.answer(f"✅ Анкета #{sid} создана!\n📌 {data['title']}\n💵 {data['price']} {emoji}", reply_markup=main_kb)

@dp.message(ServiceForm.photo, F.text == "➡️ Пропустить")
async def service_skip_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    acc = get_account(message.from_user.id)
    currency = data.get("service_currency", "gold")
    sid = create_service(acc[0], data["title"], data["description"], data["category"], data["price"], currency)
    try: await message.delete()
    except: pass
    await state.clear()
    emoji = "💰" if currency == "gold" else "🥔"
    await message.answer(f"✅ Анкета #{sid} создана!\n📌 {data['title']}\n💵 {data['price']} {emoji}", reply_markup=main_kb)

@dp.message(ServiceForm.photo)
async def service_photo_wrong(message: Message):
    await message.answer("Пришли фото или «➡️ Пропустить».")

@dp.message(F.text == "🏪 Все анкеты")
async def services_list(message: Message):
    try: await message.delete()
    except: pass
    services = get_services('gold')
    if not services:
        await message.answer("Анкет нет."); return
    for s in services:
        author = get_account_by_id(s[1])
        promo = "🔥 " if s[8] else ""
        text = (f"🏪 {promo}Анкета #{s[0]}\n👤 {author[2] if author else '?'}\n"
                f"📌 {s[2]}\n📚 {s[4]}\n📝 {s[3]}\n💵 {s[5]} 💰")
        acc = get_account(message.from_user.id)
        btns = [[InlineKeyboardButton(text="🛒 Купить", callback_data=f"buy_{s[0]}")]]
        if acc and s[1] == acc[0]:
            btns.append([InlineKeyboardButton(text="🔥 Продвинуть (50 🥔)", callback_data=f"promo_{s[0]}")])
        kb = InlineKeyboardMarkup(inline_keyboard=btns)
        if s[7]:
            await message.answer_photo(photo=s[7], caption=text, reply_markup=kb)
        else:
            await message.answer(text, reply_markup=kb)

@dp.message(F.text == "📁 Мои анкеты")
async def my_services(message: Message):
    try: await message.delete()
    except: pass
    acc = get_account(message.from_user.id)
    if not acc:
        await message.answer("Сначала /start"); return
    services = get_my_services(acc[0], 'gold')
    if not services:
        await message.answer("У тебя нет анкет."); return
    for s in services:
        text = f"🏪 #{s[0]}\n📌 {s[2]}\n💵 {s[5]} 💰"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delserv_{s[0]}")],
            [InlineKeyboardButton(text="🔥 Продвинуть (50 🥔)", callback_data=f"promo_{s[0]}")]
        ])
        await message.answer(text, reply_markup=kb)

@dp.callback_query(F.data.startswith("delserv_"))
async def delete_service(callback: CallbackQuery):
    sid = int(callback.data.split("_")[1])
    s = get_service(sid)
    acc = get_account(callback.from_user.id)
    if not s or s[1] != acc[0]:
        await callback.answer("Не твоя.", show_alert=True); return
    cur.execute("UPDATE services SET status = 'deleted' WHERE id = ?", (sid,))
    conn.commit()
    await callback.message.edit_text(callback.message.text + "\n\n🗑 Удалено.")
    await callback.answer()

@dp.callback_query(F.data.startswith("promo_"))
async def promote_service(callback: CallbackQuery):
    sid = int(callback.data.split("_")[1])
    s = get_service(sid)
    acc = get_account(callback.from_user.id)
    if not s or s[1] != acc[0]:
        await callback.answer("Не твоя.", show_alert=True); return
    if s[8]:
        await callback.answer("Уже продвинута.", show_alert=True); return
    if acc[4] < 50:
        await callback.answer("Нужно 50 🥔.", show_alert=True); return
    add_koch(acc[0], -50, f"Продвижение #{sid}")
    cur.execute("UPDATE services SET promoted = 1 WHERE id = ?", (sid,))
    conn.commit()
    await callback.answer("В топе!")
    await callback.message.answer(f"🔥 Анкета #{sid} продвинута! (-50 🥔)")

@dp.callback_query(F.data.startswith("buy_"))
async def buy_service(callback: CallbackQuery):
    sid = int(callback.data.split("_")[1])
    s = get_service(sid)
    if not s or s[9] != "active":
        await callback.answer("Недоступна.", show_alert=True); return
    acc = get_account(callback.from_user.id)
    if not acc:
        await callback.answer("Сначала /start", show_alert=True); return
    if s[1] == acc[0]:
        await callback.answer("Нельзя свою.", show_alert=True); return
    if s[6] != 'gold':
        await callback.answer("Не за голду.", show_alert=True); return
    if acc[3] < s[5]:
        await callback.answer(f"Мало голды. Нужно {s[5]}.", show_alert=True); return
    cur.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", (s[5], acc[0]))
    conn.commit()
    log_tx(acc[0], "purchase", -s[5], None, f"Покупка анкеты #{sid}")
    order_id = create_order(acc[0], s[2], s[3], "по анкете", s[5], s[7])
    cur.execute("UPDATE orders SET executor_id = ?, status = 'taken' WHERE id = ?", (s[1], order_id))
    cur.execute("UPDATE accounts SET frozen = frozen + ? WHERE id = ?", (s[5], acc[0]))
    conn.commit()
    await callback.answer("Куплено!")
    await callback.message.answer(f"✅ Куплена анкета #{sid}\nЗаказ #{order_id}\nСписано: {s[5]} 💰 (заморожено)")
    seller = get_account_by_id(s[1])
    if seller:
        try:
            await bot.send_message(seller[1], f"🎉 Купили анкету #{sid}!\nЗаказ #{order_id}\nПокупатель: {acc[2]}")
        except: pass

@dp.message(F.text == "🥔 Коч-Магазин")
async def btn_koch_shop(message: Message):
    try: await message.delete()
    except: pass
    await message.answer("🥔 Коч-Магазин:", reply_markup=koch_shop_kb)

@dp.message(F.text == "➕ Создать коч-анкету")
async def koch_service_start(message: Message, state: FSMContext):
    try: await message.delete()
    except: pass
    acc = get_account(message.from_user.id)
    if not acc:
        await message.answer("Сначала /start"); return
    await state.update_data(service_currency='koch')
    await message.answer("Шаг 1/5: Заголовок?", reply_markup=cancel_kb)
    await state.set_state(ServiceForm.title)

@dp.message(F.text == "🥔 Все коч-анкеты")
async def koch_services_list(message: Message):
    try: await message.delete()
    except: pass
    services = get_services('koch')
    if not services:
        await message.answer("Анкет нет."); return
    for s in services:
        author = get_account_by_id(s[1])
        promo = "🔥 " if s[8] else ""
        text = (f"🥔 {promo}Анкета #{s[0]}\n👤 {author[2] if author else '?'}\n"
                f"📌 {s[2]}\n📚 {s[4]}\n📝 {s[3]}\n💵 {s[5]} 🥔")
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🛒 Купить", callback_data=f"buyk_{s[0]}")]])
        if s[7]:
            await message.answer_photo(photo=s[7], caption=text, reply_markup=kb)
        else:
            await message.answer(text, reply_markup=kb)

@dp.message(F.text == "📁 Мои коч-анкеты")
async def my_koch_services(message: Message):
    try: await message.delete()
    except: pass
    acc = get_account(message.from_user.id)
    if not acc:
        await message.answer("Сначала /start"); return
    services = get_my_services(acc[0], 'koch')
    if not services:
        await message.answer("У тебя нет коч-анкет."); return
    for s in services:
        text = f"🥔 #{s[0]}\n📌 {s[2]}\n💵 {s[5]} 🥔"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delserv_{s[0]}")]
        ])
        await message.answer(text, reply_markup=kb)

@dp.callback_query(F.data.startswith("buyk_"))
async def buy_koch_service(callback: CallbackQuery):
    sid = int(callback.data.split("_")[1])
    s = get_service(sid)
    if not s or s[9] != "active":
        await callback.answer("Недоступна.", show_alert=True); return
    acc = get_account(callback.from_user.id)
    if not acc:
        await callback.answer("Сначала /start", show_alert=True); return
    if s[1] == acc[0]:
        await callback.answer("Нельзя свою.", show_alert=True); return
    if s[6] != 'koch':
        await callback.answer("Не за коч.", show_alert=True); return
    if acc[4] < s[5]:
        await callback.answer(f"Мало коч. Нужно {s[5]}.", show_alert=True); return
    add_koch(acc[0], -s[5], f"Покупка коч-анкеты #{sid}")
    cur.execute("UPDATE accounts SET koch = koch + ? WHERE id = ?", (s[5], s[1]))
    conn.commit()
    await callback.answer("Куплено!")
    await callback.message.answer(f"✅ Куплена коч-анкета #{sid}\nСписано: {s[5]} 🥔")
    seller = get_account_by_id(s[1])
    if seller:
        try:
            await bot.send_message(seller[1], f"🥔 Купили коч-анкету #{sid}!\n+{s[5]} 🥔")
        except: pass

# ===== ЧАТ =====
@dp.callback_query(F.data.startswith("chat_"))
async def chat_open(callback: CallbackQuery, state: FSMContext):
    order_id = int(callback.data.split("_")[1])
    acc = get_account(callback.from_user.id)
    order = get_order(order_id)
    if not order:
        await callback.answer("Не найден.", show_alert=True); return
    if acc[0] != order[1] and acc[0] != order[2]:
        await callback.answer("Не участник.", show_alert=True); return
    other_id = order[2] if acc[0] == order[1] else order[1]
    other = get_account_by_id(other_id)
    await state.update_data(chat_order_id=order_id, chat_other_id=other_id)
    await callback.message.answer(
        f"💬 Чат по заказу #{order_id}\n"
        f"Собеседник: {other[2] if other else '?'}\n\n"
        f"Пиши текст или фото.\nВыйти: /endchat",
        reply_markup=cancel_kb
    )
    await state.set_state(ChatForm.message)
    await callback.answer()

@dp.message(ChatForm.message, F.text == "❌ Отмена")
async def chat_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Чат закрыт.", reply_markup=main_kb)

@dp.message(ChatForm.message, F.text == "/endchat")
async def chat_end(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Чат закрыт.", reply_markup=main_kb)

@dp.message(ChatForm.message, F.text)
async def chat_send_text(message: Message, state: FSMContext):
    data = await state.get_data()
    order_id = data.get("chat_order_id")
    other_id = data.get("chat_other_id")
    if not order_id or not other_id:
        await state.clear()
        await message.answer("Чат закрыт.", reply_markup=main_kb)
        return
    acc = get_account(message.from_user.id)
    other = get_account_by_id(other_id)
    if not other:
        return
    save_chat_message(order_id, acc[0], other_id, "text", message.text)
    try:
        await bot.send_message(other[1], f"💬 Заказ #{order_id}\nОт: {acc[2]}\n\n{message.text}")
    except: pass
    try: await message.delete()
    except: pass
    await message.answer("✅ Отправлено.")

@dp.message(ChatForm.message, F.photo)
async def chat_send_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    order_id = data.get("chat_order_id")
    other_id = data.get("chat_other_id")
    if not order_id or not other_id:
        await state.clear()
        await message.answer("Чат закрыт.", reply_markup=main_kb)
        return
    acc = get_account(message.from_user.id)
    other = get_account_by_id(other_id)
    if not other:
        return
    photo_id = message.photo[-1].file_id
    caption = message.caption or ""
    save_chat_message(order_id, acc[0], other_id, "photo", caption, photo_id)
    try:
        await bot.send_photo(other[1], photo=photo_id, caption=f"💬 Заказ #{order_id}\nОт: {acc[2]}\n{caption}")
    except: pass
    try: await message.delete()
    except: pass
    await message.answer("✅ Фото отправлено.")

# ===== ОТЗЫВЫ =====
@dp.callback_query(F.data.startswith("review_"))
async def review_start(callback: CallbackQuery, state: FSMContext):
    order_id = int(callback.data.split("_")[1])
    acc = get_account(callback.from_user.id)
    order = get_order(order_id)
    if not order or order[1] != acc[0]:
        await callback.answer("Не твой.", show_alert=True); return
    if order[9] != "done":
        await callback.answer("Не завершён.", show_alert=True); return
    await state.update_data(review_order_id=order_id, review_executor_id=order[2])
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="1⭐"), KeyboardButton(text="2⭐"), KeyboardButton(text="3⭐")],
        [KeyboardButton(text="4⭐"), KeyboardButton(text="5⭐")],
        [KeyboardButton(text="❌ Отмена")]
    ], resize_keyboard=True)
    await callback.message.answer(f"⭐ Оцени исполнителя за заказ #{order_id}:", reply_markup=kb)
    await state.set_state(ReviewForm.rating)
    await callback.answer()

@dp.message(ReviewForm.rating, F.text)
async def review_rating(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_kb)
        return
    if message.text not in ["1⭐", "2⭐", "3⭐", "4⭐", "5⭐"]:
        await message.answer("1⭐-5⭐"); return
    await state.update_data(review_rating=int(message.text[0]))
    try: await message.delete()
    except: pass
    await message.answer("📝 Текст отзыва:", reply_markup=cancel_kb)
    await state.set_state(ReviewForm.text)

@dp.message(ReviewForm.text, F.text)
async def review_text(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_kb)
        return
    data = await state.get_data()
    acc = get_account(message.from_user.id)
    add_review(data["review_order_id"], acc[0], data["review_executor_id"], data["review_rating"], message.text)
    try: await message.delete()
    except: pass
    executor = get_account_by_id(data["review_executor_id"])
    if executor:
        try:
            await bot.send_message(executor[1], f"⭐ Новый отзыв за заказ #{data['review_order_id']}!\n{data['review_rating']}/5\n{message.text}")
        except: pass
    await state.clear()
    await message.answer(f"✅ Отзыв сохранён! {data['review_rating']}⭐", reply_markup=main_kb)

# ===== СПОРЫ =====
@dp.callback_query(F.data.startswith("dispute_"))
async def dispute_start(callback: CallbackQuery, state: FSMContext):
    order_id = int(callback.data.split("_")[1])
    acc = get_account(callback.from_user.id)
    order = get_order(order_id)
    if not order:
        await callback.answer("Не найден.", show_alert=True); return
    if acc[0] != order[1] and acc[0] != order[2]:
        await callback.answer("Не участник.", show_alert=True); return
    await state.update_data(dispute_order_id=order_id)
    await callback.message.answer(f"⚖️ Спор по заказу #{order_id}\n\nОпиши проблему:", reply_markup=cancel_kb)
    await state.set_state(DisputeForm.reason)
    await callback.answer()

@dp.message(DisputeForm.reason, F.text)
async def dispute_reason(message: Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_kb)
        return
    data = await state.get_data()
    acc = get_account(message.from_user.id)
    order_id = data["dispute_order_id"]
    order = get_order(order_id)
    dispute_id = create_dispute(order_id, acc[0], message.text)
    try: await message.delete()
    except: pass
    await state.clear()
    await message.answer("✅ Спор отправлен.", reply_markup=main_kb)
    try:
        customer = get_account_by_id(order[1])
        executor = get_account_by_id(order[2]) if order[2] else None
        await bot.send_message(
            ADMIN_ID,
            f"⚖️ Спор #{dispute_id}\n"
            f"Заказ #{order_id}: {order[3]}\n"
            f"Сумма: {order[6]} 💰\n"
            f"Заказчик: {customer[2] if customer else '?'}\n"
            f"Исполнитель: {executor[2] if executor else 'нет'}\n\n"
            f"От {acc[2]}: {message.text}\n\n"
            f"/resolve {dispute_id} refund|payout|split"
        )
    except: pass

# ===== АДМИНКА =====
@dp.message(Command("admin"))
async def admin_panel(message: Message):
    if not is_admin(message.from_user.id): return
    try: await message.delete()
    except: pass
    await message.answer(
        "Панель:\n\n"
        "📰 /news — новость\n/delnews ID\n\n"
        "💰 /give_gold НИК СУММА\n/give_koch НИК СУММА\n/self_gold СУММА\n/self_koch СУММА\n\n"
        "🚫 /ban НИК\n/unban НИК\n\n"
        "💸 /withdraws\n/approve_withdraw ID\n/reject_withdraw ID\n\n"
        "⚖️ /disputes\n/resolve ID refund|payout|split\n\n"
        "💬 /chatlog ORDER_ID\n\n"
        "📊 /stats2"
    )

@dp.message(Command("news"))
async def news_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    try: await message.delete()
    except: pass
    await message.answer("📰 Заголовок:", reply_markup=cancel_kb)
    await state.set_state(NewsForm.title)

@dp.message(NewsForm.title, F.text)
async def news_title(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_kb)
        return
    await state.update_data(title=message.text)
    try: await message.delete()
    except: pass
    await message.answer("📝 Текст новости:")
    await state.set_state(NewsForm.text)

@dp.message(NewsForm.text, F.text)
async def news_text(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id): return
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("Отменено.", reply_markup=main_kb)
        return
    data = await state.get_data()
    news_id = create_news(message.from_user.id, data["title"], message.text)
    try: await message.delete()
    except: pass
    await state.clear()
    await message.answer(f"✅ Новость #{news_id}!", reply_markup=main_kb)

@dp.message(Command("delnews"))
async def del_news(message: Message):
    if not is_admin(message.from_user.id): return
    try: await message.delete()
    except: pass
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Формат: /delnews ID"); return
    cur.execute("UPDATE news SET status = 'deleted' WHERE id = ?", (int(parts[1]),))
    conn.commit()
    await message.answer(f"🗑 #{parts[1]} удалена.")

@dp.message(Command("give_gold"))
async def admin_give_gold(message: Message):
    if not is_admin(message.from_user.id): return
    try: await message.delete()
    except: pass
    parts = message.text.split()
    if len(parts) != 3:
        await message.answer("Формат: /give_gold НИК СУММА"); return
    acc = get_account_by_nick(parts[1])
    if not acc:
        await message.answer("Нет ника."); return
    if not parts[2].isdigit():
        await message.answer("Сумма — число."); return
    add_gold(acc[0], int(parts[2]), "Начисление")
    await message.answer(f"✅ {parts[1]}: +{parts[2]} 💰")

@dp.message(Command("give_koch"))
async def admin_give_koch(message: Message):
    if not is_admin(message.from_user.id): return
    try: await message.delete()
    except: pass
    parts = message.text.split()
    if len(parts) != 3:
        await message.answer("Формат: /give_koch НИК СУММА"); return
    acc = get_account_by_nick(parts[1])
    if not acc:
        await message.answer("Нет ника."); return
    if not parts[2].isdigit():
        await message.answer("Сумма — число."); return
    add_koch(acc[0], int(parts[2]), "Начисление")
    await message.answer(f"✅ {parts[1]}: +{parts[2]} 🥔")

@dp.message(Command("self_gold"))
async def admin_self_gold(message: Message):
    if not is_admin(message.from_user.id): return
    try: await message.delete()
    except: pass
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Формат: /self_gold СУММА"); return
    acc = get_account(message.from_user.id)
    add_gold(acc[0], int(parts[1]), "Пополнение")
    await message.answer(f"✅ +{parts[1]} 💰")

@dp.message(Command("self_koch"))
async def admin_self_koch(message: Message):
    if not is_admin(message.from_user.id): return
    try: await message.delete()
    except: pass
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Формат: /self_koch СУММА"); return
    acc = get_account(message.from_user.id)
    add_koch(acc[0], int(parts[1]), "Пополнение")
    await message.answer(f"✅ +{parts[1]} 🥔")

@dp.message(Command("ban"))
async def admin_ban(message: Message):
    if not is_admin(message.from_user.id): return
    try: await message.delete()
    except: pass
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("Формат: /ban НИК"); return
    acc = get_account_by_nick(parts[1])
    if not acc:
        await message.answer("Нет ника."); return
    cur.execute("UPDATE accounts SET is_banned = 1 WHERE id = ?", (acc[0],))
    conn.commit()
    await message.answer(f"✅ {parts[1]} забанен.")

@dp.message(Command("unban"))
async def admin_unban(message: Message):
    if not is_admin(message.from_user.id): return
    try: await message.delete()
    except: pass
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("Формат: /unban НИК"); return
    acc = get_account_by_nick(parts[1])
    if not acc:
        await message.answer("Нет ника."); return
    cur.execute("UPDATE accounts SET is_banned = 0 WHERE id = ?", (acc[0],))
    conn.commit()
    await message.answer(f"✅ {parts[1]} разбанен.")

@dp.message(Command("withdraws"))
async def admin_withdraws(message: Message):
    if not is_admin(message.from_user.id): return
    try: await message.delete()
    except: pass
    cur.execute("SELECT * FROM withdraw_requests WHERE status = 'pending' ORDER BY id DESC")
    reqs = cur.fetchall()
    if not reqs:
        await message.answer("Заявок нет."); return
    for r in reqs:
        acc = get_account_by_id(r[1])
        await message.answer(
            f"💸 Заявка #{r[0]}\nЮзер: {acc[2] if acc else '?'}\n"
            f"Голда: {r[2]} 💰\nЗвёзды: {r[3]} ⭐\n\n"
            f"/approve_withdraw {r[0]}\n/reject_withdraw {r[0]}"
        )

@dp.message(Command("approve_withdraw"))
async def admin_approve_withdraw(message: Message):
    if not is_admin(message.from_user.id): return
    try: await message.delete()
    except: pass
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Формат: /approve_withdraw ID"); return
    req_id = int(parts[1])
    cur.execute("SELECT * FROM withdraw_requests WHERE id = ?", (req_id,))
    r = cur.fetchone()
    if not r or r[4] != "pending":
        await message.answer("Не найдена."); return
    cur.execute("UPDATE withdraw_requests SET status = 'approved' WHERE id = ?", (req_id,))
    conn.commit()
    acc = get_account_by_id(r[1])
    await message.answer(f"✅ #{req_id} одобрена. Отправь {r[3]} ⭐ вручную!")
    if acc:
        try:
            await bot.send_message(acc[1], f"✅ Заявка #{req_id} одобрена! Админ отправит {r[3]} ⭐.")
        except: pass

@dp.message(Command("reject_withdraw"))
async def admin_reject_withdraw(message: Message):
    if not is_admin(message.from_user.id): return
    try: await message.delete()
    except: pass
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Формат: /reject_withdraw ID"); return
    req_id = int(parts[1])
    cur.execute("SELECT * FROM withdraw_requests WHERE id = ?", (req_id,))
    r = cur.fetchone()
    if not r or r[4] != "pending":
        await message.answer("Не найдена."); return
    cur.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (r[2], r[1]))
    conn.commit()
    log_tx(r[1], "withdraw_refund", r[2], None, f"Заявка #{req_id} отклонена")
    cur.execute("UPDATE withdraw_requests SET status = 'rejected' WHERE id = ?", (req_id,))
    conn.commit()
    acc = get_account_by_id(r[1])
    await message.answer(f"❌ #{req_id} отклонена. Голда возвращена.")
    if acc:
        try:
            await bot.send_message(acc[1], f"❌ Заявка #{req_id} отклонена. {r[2]} 💰 возвращено.")
        except: pass

@dp.message(Command("chatlog"))
async def admin_chatlog(message: Message):
    if not is_admin(message.from_user.id): return
    try: await message.delete()
    except: pass
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Формат: /chatlog ORDER_ID"); return
    order_id = int(parts[1])
    order = get_order(order_id)
    if not order:
        await message.answer("Заказ не найден."); return
    msgs = get_chat_history(order_id)
    if not msgs:
        await message.answer(f"Переписки нет."); return
    text = f"💬 Переписка по заказу #{order_id}\n📌 {order[3]}\n\n"
    for m in msgs:
        sender = get_account_by_id(m[2])
        content = m[5] if m[5] else f"[{m[4]}]"
        text += f"[{m[7][:16]}] {sender[2] if sender else '?'}: {content}\n"
        if len(text) > 3500:
            await message.answer(text)
            text = ""
    if text:
        await message.answer(text)

@dp.message(Command("disputes"))
async def admin_disputes(message: Message):
    if not is_admin(message.from_user.id): return
    try: await message.delete()
    except: pass
    cur.execute("SELECT * FROM disputes WHERE status = 'open' ORDER BY id DESC")
    disputes = cur.fetchall()
    if not disputes:
        await message.answer("Споров нет."); return
    for d in disputes:
        order = get_order(d[1])
        author = get_account_by_id(d[2])
        await message.answer(
            f"⚖️ Спор #{d[0]}\nЗаказ #{d[1]}: {order[3] if order else '?'}\n"
            f"Сумма: {order[6] if order else '?'} 💰\n"
            f"Автор: {author[2] if author else '?'}\nПричина: {d[3]}\n\n"
            f"/resolve {d[0]} refund|payout|split"
        )

@dp.message(Command("resolve"))
async def admin_resolve(message: Message):
    if not is_admin(message.from_user.id): return
    try: await message.delete()
    except: pass
    parts = message.text.split()
    if len(parts) != 3 or parts[2] not in ("refund", "payout", "split"):
        await message.answer("Формат: /resolve ID refund|payout|split"); return
    if not parts[1].isdigit():
        await message.answer("ID — число."); return
    dispute_id = int(parts[1])
    action = parts[2]
    cur.execute("SELECT * FROM disputes WHERE id = ?", (dispute_id,))
    dispute = cur.fetchone()
    if not dispute:
        await message.answer("Не найден."); return
    order_id = dispute[1]
    order = get_order(order_id)
    if not order:
        await message.answer("Заказ не найден."); return
    amount = order[6]
    if action == "refund":
        unfreeze_to_customer(order[1], amount, order_id, "Спор: возврат")
    elif action == "payout":
        unfreeze_to_executor(order[1], order[2], amount, order_id)
    elif action == "split":
        half = amount // 2
        cur.execute("UPDATE accounts SET frozen = frozen - ? WHERE id = ?", (amount, order[1]))
        cur.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (half, order[1]))
        cur.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", (int(half * 0.85), order[2]))
        conn.commit()
        log_tx(order[1], "dispute_refund", half, order_id, "Спор: 50/50")
    cur.execute("UPDATE orders SET status = 'done' WHERE id = ?", (order_id,))
    cur.execute("UPDATE disputes SET status = 'closed' WHERE id = ?", (dispute_id,))
    conn.commit()
    await message.answer(f"✅ Спор #{dispute_id}: {action}")

async def show_stats2(message: Message):
    cur.execute("SELECT COUNT(*) FROM accounts"); users = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM orders"); orders = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM orders WHERE status = 'done'"); done = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM services WHERE status = 'active'"); services = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM disputes WHERE status = 'open'"); disp = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM withdraw_requests WHERE status = 'pending'"); wd = cur.fetchone()[0]
    cur.execute("SELECT SUM(balance) FROM accounts"); gold = cur.fetchone()[0] or 0
    cur.execute("SELECT SUM(koch) FROM accounts"); koch = cur.fetchone()[0] or 0
    text = (
        f"📊 СТАТИСТИКА 2.0 (админ)\n\n"
        f"👥 Юзеров: {users}\n"
        f"📦 Заказов: {orders} (✅ {done})\n"
        f"🏪 Услуг: {services}\n"
        f"⚖️ Споров: {disp}\n"
        f"💸 Заявок на вывод: {wd}\n"
        f"💰 Голды: {gold}\n"
        f"🥔 Коч-коинов: {koch}\n\n"
        f"👤 Все юзеры:\n"
    )
    cur.execute("SELECT nickname, tg_id, balance, koch, rating FROM accounts ORDER BY id ASC")
    all_users = cur.fetchall()
    for u in all_users:
        try:
            chat = await bot.get_chat(u[1])
            uname = f"@{chat.username}" if chat.username else f"ID:{u[1]}"
        except:
            uname = f"ID:{u[1]}"
        text += f"\n{u[0]} → {uname} | 💰 {u[2]} | 🥔 {u[3]} | ⭐ {u[4] or 0}"
        if len(text) > 3500:
            await message.answer(text)
            text = ""
    if text:
        await message.answer(text)

@dp.message(Command("stats2"))
async def admin_stats2(message: Message):
    if not is_admin(message.from_user.id): return
    try: await message.delete()
    except: pass
    await show_stats2(message)

async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
