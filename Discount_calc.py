import telebot
import os
from dotenv import load_dotenv
from telebot import types

# загружаем переменные из .env
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode='Markdown')
# снимаем вебхук, чтобы не было конфликта с polling
bot.remove_webhook()

# простое хранение состояния диалога: price/discount
user_state = {}

def get_main_kb() -> types.ReplyKeyboardMarkup:
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(types.KeyboardButton('▶️ Старт'), types.KeyboardButton('❓ Помощь'))
    return kb

# функция для выбора эмодзи по размеру скидки
def discount_mood(discount: float) -> str:
    d = discount
    if d < 10:
        return '🙂'
    elif d < 25:
        return '💸'
    elif d < 40:
        return '😮💸'
    elif d < 55:
        return '🔥💸'
    elif d < 70:
        return '🚨🔥'
    elif d < 85:
        return '🚨🔥🔥'
    else:
        return '😱🚨🔥🔥'

def format_bill(price: float, discount: int, final_price: float) -> str:
    """Возвращает красивый ответ с эмодзи и жирными подписями."""
    emo = discount_mood(discount)
    bar = '━━━━━━━━━━━━━━━━━━━━'
    msg = (
        f"💳 *Калькулятор скидок*\n"
        f"{bar}\n"
        f"💰 **Цена без скидки:** *{price:.2f} руб.*\n"
        f"🎁 **Скидка:** *{round(discount)}%* {emo}\n"
        f"✅ **Цена с учётом скидки:** *{final_price:.2f} руб.*\n"
    )
    # Дополнительные подсказки по величине скидки
    if discount >= 70:
        msg += "⚠️ Это уже что-то из ряда вон! 🤯\n"
    elif discount >= 50:
        msg += "🔥 Горячее предложение!\n"
    msg += bar
    return msg

@bot.message_handler(commands=['start'])
def start(m):
    chat_id = m.chat.id
    user_state[chat_id] = {'stage': 'price'}
    bot.reply_to(
        m,
        "🎉 *Калькулятор скидок!* \n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "💰 Введи цену (например: `100,50`).\n"
        "🎁 Скидка в % (например: `15`).\n"
        "🛑 Для выхода напиши «стоп».",
        reply_markup=get_main_kb()
    )

@bot.message_handler(commands=['help'])
def help_cmd(m):
    bot.reply_to(
        m,
        "ℹ️ *Как пользоваться*\n"
        "1. Введи цену (например: 1999,90)\n"
        "2. Укажи скидку (например: 15)\n"
        "3. Получи чек с итогом\n"
        "🛑 Для выхода напиши «стоп».",
        reply_markup=get_main_kb()
    )

@bot.message_handler(func=lambda m: True)
def handle(m):
    chat_id = m.chat.id
    text = m.text.strip()
    low = text.lower()

    # обработка кнопок «Старт» и «Помощь»
    if 'старт' in low or text.startswith('▶️') or low == '/start':
        start(m)
        return
    if 'помощ' in low or text.startswith('❓') or low == '/help':
        help_cmd(m)
        return

    if low == 'стоп':
        user_state.pop(chat_id, None)
        bot.reply_to(m, "👋 До встречи! Когда понадобится — пиши /start", reply_markup=get_main_kb())
        return

    # получаем текущее состояние (по умолчанию ждём цену)
    state = user_state.get(chat_id, {'stage': 'price'})

    try:
        if state['stage'] == 'price':
            # поддержим запятую как разделитель
            price = float(text.replace(',', '.'))
            if price <= 0:
                bot.reply_to(
                    m,
                    "⚠️ Цена должна быть > 0.\n"
                    "💰 Введи цену (например: `100,50`).",
                    reply_markup=get_main_kb()
                )
                return
            # сохраняем цену и просим скидку
            user_state[chat_id] = {'stage': 'discount', 'price': price}
            bot.reply_to(
                m,
                "━━━━━━━━━━━━━━━━━━━━\n"
                "🎁 Укажи скидку % (например: `15`).",
                reply_markup=get_main_kb()
            )
            return

        elif state['stage'] == 'discount':
            discount = int(float(text.replace(',', '.')))
            if not (0 < discount < 100):
                bot.reply_to(
                    m,
                    "⚠️ Скидка должна быть 1–99.\n"
                    "🎁 Введи целое число (например: `15`).",
                    reply_markup=get_main_kb()
                )
                return
            price = state['price']
            final_price = float(price * (1 - discount / 100.0))
            msg = format_bill(price, discount, float(final_price))
            bot.reply_to(m, msg, reply_markup=get_main_kb())
            # возвращаемся к этапу ввода новой цены
            user_state[chat_id] = {'stage': 'price'}
            return

        else:
            # на всякий случай сбрасываемся
            user_state[chat_id] = {'stage': 'price'}
            bot.reply_to(
                m,
                "💰 Введи цену (например: `100,50`).",
                reply_markup=get_main_kb()
            )
            return
    except ValueError:
        bot.reply_to(m, "Введи число (например: 1999.90) или «стоп».", reply_markup=get_main_kb())

bot.polling(none_stop=True, skip_pending=True)