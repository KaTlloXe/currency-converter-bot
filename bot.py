import telebot
import requests
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from config import TOKEN

bot = telebot.TeleBot(TOKEN)

# Валюти
SUPPORTED_CURRENCIES = ["UAH", "USD", "EUR", "GBP", "CAD", "PLN", "RON"]

# Стан користувача
user_states = {}
user_data = {}
user_base_currency = {}

# Клавіатура
MENU_CONVERT = "🔄 Конвертувати валюту"
MENU_RATES = "📊 Курс валют"
MENU_SETBASE = "⚙️ Змінити базову валюту"
MENU_HELP = "ℹ️ Допомога"

# Головне меню
main_menu = ReplyKeyboardMarkup(resize_keyboard=True)
main_menu.add(
    KeyboardButton(MENU_CONVERT),
    KeyboardButton(MENU_RATES),
    KeyboardButton(MENU_SETBASE),
    KeyboardButton(MENU_HELP)
)

# Клавіатура валют
def currency_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for i in range(0, len(SUPPORTED_CURRENCIES), 2):
        buttons = [KeyboardButton(SUPPORTED_CURRENCIES[i])]
        if i + 1 < len(SUPPORTED_CURRENCIES):
            buttons.append(KeyboardButton(SUPPORTED_CURRENCIES[i + 1]))
        kb.row(*buttons)
    return kb

# Отримати всі курси
def get_all_rates(base_currency):
    try:
        url = f"https://open.er-api.com/v6/latest/{base_currency}"
        response = requests.get(url)
        data = response.json()
        if data.get("result") == "success":
            return data["rates"]
    except Exception as e:
        print(f"Помилка при отриманні курсів: {e}")
    return None

# Отримати конкретний курс
def get_rate(base, target):
    rates = get_all_rates(base)
    return rates.get(target) if rates and target in rates else None

# /start
@bot.message_handler(commands=["start"])
def start(message):
    user_base_currency[message.chat.id] = "UAH"
    bot.send_message(
        message.chat.id,
        "👋 Привіт! Я бот-конвертер валют.\nНатисни /convert для початку.",
        reply_markup=main_menu
    )

# /help
@bot.message_handler(commands=["help"])
def help_command(message):
    text = (
        "📘 Команди:\n"
        "/convert – конвертація валют\n"
        "/rates – курси для базової валюти\n"
        "/setbase – змінити базову валюту\n"
        "/help – довідка\n\n"
        "Підтримувані валюти: UAH, USD, EUR, GBP, CAD, PLN, RON"
    )
    bot.send_message(message.chat.id, text)

# /setbase
@bot.message_handler(commands=["setbase"])
def set_base_currency(message):
    user_states[message.chat.id] = "awaiting_base_set"
    bot.send_message(message.chat.id, "🔧 Обери нову базову валюту:", reply_markup=currency_keyboard())

# /rates
@bot.message_handler(commands=["rates"])
def rates(message):
    base = user_base_currency.get(message.chat.id, "UAH")
    targets = [cur for cur in SUPPORTED_CURRENCIES if cur != base]
    rates = get_all_rates(base)
    if rates:
        text = f"📊 Курси 1 {base}:\n"
        for target in targets:
            if target in rates:
                text += f"➡️ {target}: {round(rates[target], 4)}\n"
        bot.send_message(message.chat.id, text)
    else:
        bot.send_message(message.chat.id, "❌ Помилка завантаження курсів.")

# /convert
@bot.message_handler(commands=["convert"])
def convert_start(message):
    user_states[message.chat.id] = "awaiting_base_currency"
    bot.send_message(message.chat.id, "💱 Обери валюту, яку хочеш конвертувати:", reply_markup=currency_keyboard())

@bot.message_handler(func=lambda m: True)
def handle_text(message):
    chat_id = message.chat.id
    state = user_states.get(chat_id)
    text = message.text.strip()

    if text == MENU_CONVERT:
        return convert_start(message)
    elif text == MENU_RATES:
        return rates(message)
    elif text == MENU_SETBASE:
        return set_base_currency(message)
    elif text == MENU_HELP:
        return help_command(message)

    if state == "awaiting_base_set":
        currency = message.text.upper()
        if currency in SUPPORTED_CURRENCIES:
            user_base_currency[chat_id] = currency
            bot.send_message(chat_id, f"✅ Базову валюту змінено на {currency}.", reply_markup=main_menu)
        else:
            bot.send_message(chat_id, "❌ Непідтримувана валюта.")
        user_states[chat_id] = None

    elif state == "awaiting_base_currency":
        base = message.text.upper()
        if base in SUPPORTED_CURRENCIES:
            user_data[chat_id] = {"base": base}
            user_states[chat_id] = "awaiting_target_currency"
            bot.send_message(chat_id, "➡️ Обери валюту, в яку хочеш конвертувати:", reply_markup=currency_keyboard())
        else:
            bot.send_message(chat_id, "❌ Валюта не підтримується.", reply_markup=main_menu)

    elif state == "awaiting_target_currency":
        target = message.text.upper()
        if target in SUPPORTED_CURRENCIES:
            user_data[chat_id]["target"] = target
            user_states[chat_id] = "awaiting_amount"
            bot.send_message(chat_id, f"💰 Введи суму в {user_data[chat_id]['base']}:", reply_markup=ReplyKeyboardRemove())
        else:
            bot.send_message(chat_id, "❌ Валюта не підтримується.", reply_markup=main_menu)

    elif state == "awaiting_amount":
        try:
            amount = float(message.text.replace(",", "."))
            if amount <= 0:
                bot.send_message(chat_id, "❗ Сума має бути більшою за 0.", reply_markup=main_menu)    
                return            
            base = user_data[chat_id]["base"]
            target = user_data[chat_id]["target"]
            rate = get_rate(base, target)
            if rate is not None:
                result = round(amount * rate, 2)
                bot.send_message(chat_id, f"✅ {amount} {base} = {result} {target}", reply_markup=main_menu)
            else:
                bot.send_message(chat_id, "⚠️ Курс недоступний.")
        except ValueError:
            bot.send_message(chat_id, "❗ Введіть числове значення (наприклад: 1000)")
            return  # не скидаємо стан
        finally:
            if user_states.get(chat_id) == "awaiting_amount":
                user_states[chat_id] = None
                user_data[chat_id] = {}

    else:
        bot.send_message(chat_id, "⬇️ Обери дію з меню нижче:", reply_markup=main_menu)

# Запуск
if __name__ == "__main__":
    print("🤖 Бот запущено")
    bot.infinity_polling()
