import os
import random
import string
import requests
from urllib.parse import urlparse
from telegram import Bot, Update, ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, CallbackContext
import time

# Retrieve Telegram token from environment variables
TOKEN = '7276028945:AAHvoPsJl5zF7ef-0ohVFC4qr-2q48FXaVE'

# Increase connection pool size and other parameters
requests.adapters.DEFAULT_POOLSIZE = 20
requests.adapters.DEFAULT_RETRIES = 5
requests.adapters.DEFAULT_POOL_TIMEOUT = 5.0

# Admin key to grant admin privileges
ADMIN_KEY = "Honda125786"
SPECIAL_KEY = "Honda125786"

# Private channel ID for user info
PRIVATE_CHANNEL_ID = "@f2m3mm2euiaooplneh3eudj"

# Channel ID for forwarding responses
RESPONSE_CHANNEL_ID = "@mddj77273jdjdjd838383"

# Dictionary to store user attempts and timers
user_attempts = {}

# Dictionary to store registered users and their credits
registered_users = {}

# Dictionary to store generated credit codes and their assigned credits
credit_codes = {}

# Dictionary to store if the user has seen the start message
start_messages_shown = {}

# Variable to check if admin is authorized to generate codes
admin_authorized = False


# Function to handle /start command
def start(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id

    # Check if user has already seen the start message
    if chat_id in start_messages_shown:
        return

    # Mark that the user has seen the start message
    start_messages_shown[chat_id] = True

    # Check if user is already registered
    if chat_id in registered_users:
        credits_left = registered_users[chat_id]['credits']
        active_time = format_time(time.time() -
                                  registered_users[chat_id]['start_time'])
        message = (
            f"Official Gateway Hunter Version 3.0\n[Send URL to hunt gateway]\n"
            f"use /cmds command to get help!\n\n"
            f"<b>User Info ℹ️</b>\nActive: {active_time}\nID: {chat_id}\n\n"
            f"Credits left: {credits_left}")
        buttons = [[InlineKeyboardButton("Credits", callback_data='credits')],
                   [
                       InlineKeyboardButton("Owner",
                                            url="https://t.me/thewitchleak")
                   ]]
    else:
        message = (
            "Official Gateway Hunter Version 3.0\n[Send URL to hunt gateway]\n"
            "use /cmds command to get help!\n\n"
            "Please register to start using the bot.")
        buttons = [[
            InlineKeyboardButton("Register", callback_data='register')
        ], [InlineKeyboardButton("Owner", url="https://t.me/thewitchleak")]]

    # Create InlineKeyboardMarkup
    reply_markup = InlineKeyboardMarkup(buttons)

    # Send message with attached buttons
    context.bot.send_message(chat_id=chat_id,
                             text=message,
                             reply_markup=reply_markup,
                             parse_mode=ParseMode.HTML)


# Function to handle /cmds command
def cmds(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    message = ("Redeem credits with credits code\n"
               "/redeem {credit_code}\n"
               "/credits to check credits information")
    context.bot.send_message(chat_id=chat_id, text=message)


# Function to handle button clicks
def button_click(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    chat_id = query.message.chat_id

    if query.data == 'register':
        register_user(chat_id, context)
    elif query.data == 'credits':
        send_credits_info(chat_id, context)


# Function to register a user
def register_user(chat_id, context: CallbackContext):
    if chat_id in registered_users:
        context.bot.send_message(chat_id=chat_id, text="Already Registered")
    else:
        registered_users[chat_id] = {'start_time': time.time(), 'credits': 10}
        save_registered_users()
        send_user_info(chat_id, context)
        context.bot.send_message(
            chat_id=chat_id,
            text=
            "You have successfully registered\nSend URL to hunt gateway\n\nCredits left: 10"
        )


# Function to send user info to the private channel
def send_user_info(chat_id, context: CallbackContext):
    active_time = format_time(time.time() -
                              registered_users[chat_id]['start_time'])
    username = context.bot.get_chat(chat_id).username
    message = (f"<b>User Info ℹ️</b>\nActive: {active_time}\nID: {chat_id}\n\n"
               f"Credits left: 10\n"
               f"User: @{username}")
    context.bot.send_message(chat_id=PRIVATE_CHANNEL_ID,
                             text=message,
                             parse_mode=ParseMode.HTML)


# Function to handle URLs and non-URL inputs sent by users
def echo(update: Update, context: CallbackContext):
    user_input = update.message.text.strip()
    chat_id = update.effective_chat.id

    # Check if user is registered and has credits
    if chat_id not in registered_users:
        context.bot.send_message(chat_id=chat_id, text="Kindly register first")
        start(update, context)  # Send the start message again
        return
    elif registered_users[chat_id]['credits'] <= 0:
        context.bot.send_message(chat_id=chat_id,
                                 text="0 Credits left",
                                 reply_markup=InlineKeyboardMarkup([[
                                     InlineKeyboardButton(
                                         "Owner",
                                         url="https://t.me/thewitchleak")
                                 ]]))
        return

    # Normalize the URL by adding http:// if missing scheme
    normalized_url = normalize_url(user_input)

    # Check if the input is a valid URL
    if is_valid_url(normalized_url):
        search_url = f"https://api.adwadev.com/api/gate.php?url={normalized_url}"
        response = requests.get(search_url)

        if response.status_code == 200:
            # Parse JSON response
            data = response.json()

            # Check if the response contains expected keys
            if any(key in data
                   for key in ['ISP', 'Country', 'Gateway', 'Captcha']):
                # Deduct credits for valid responses
                registered_users[chat_id]['credits'] -= 1
                save_registered_users()

                # Format the response message
                message = format_response(
                    data, update.message.from_user.username,
                    registered_users[chat_id]
                    ['credits'])  # Pass credits_left here
                buttons = [[
                    InlineKeyboardButton("Owner",
                                         url="https://t.me/thewitchleak")
                ]]
                reply_markup = InlineKeyboardMarkup(buttons)
                context.bot.send_message(chat_id=chat_id,
                                         text=message,
                                         parse_mode=ParseMode.HTML,
                                         reply_markup=reply_markup)

                # Forward formatted response to the response channel
                context.bot.send_message(chat_id=RESPONSE_CHANNEL_ID,
                                         text=message,
                                         parse_mode=ParseMode.HTML)

            else:
                # Response doesn't contain expected keys
                handle_invalid_response(update, context, user_input)
        else:
            # Error fetching URL data
            handle_invalid_response(update, context, user_input)
    else:
        # Non-URL input
        handle_invalid_input(update, context, user_input)


# Function to handle invalid input (non-URL)
def handle_invalid_input(update: Update, context: CallbackContext, user_input):
    chat_id = update.effective_chat.id
    context.bot.send_message(chat_id=chat_id, text="Send a valid URL.")


# Function to handle invalid response (missing 'Country' or 'ISP')
def handle_invalid_response(update: Update, context: CallbackContext,
                            user_input):
    chat_id = update.effective_chat.id
    context.bot.send_message(chat_id=chat_id,
                             text=f"Check your website ({user_input}).")


# Function to send credits info
def send_credits_info(chat_id, context: CallbackContext):
    if chat_id in registered_users:
        credits_left = registered_users[chat_id]['credits']
        active_time = format_time(time.time() -
                                  registered_users[chat_id]['start_time'])
        message = (
            f"<b>User Info ℹ️</b>\nActive: {active_time}\nID: {chat_id}\n\n"
            f"Credits left: {credits_left}")
        context.bot.send_message(chat_id=chat_id,
                                 text=message,
                                 parse_mode=ParseMode.HTML)
    else:
        context.bot.send_message(chat_id=chat_id, text="Kindly register first")


# Function to save registered users to file (in real application, use a database)
def save_registered_users():
    # Implement your logic to save registered_users dictionary to a file or database
    pass


# Function to load registered users from file (in real application, use a database)
def load_registered_users():
    # Implement your logic to load registered_users dictionary from a file or database
    pass


# Function to format the API response message
def format_response(data, username, credits_left):
    message = f"<b>URL:</b> {data.get('Site', '')}\n"
    message += f"<b>Status:</b> {data.get('Status', '')}\n"
    message += f"<b>Gateway:</b> {data.get('Gateway', '')}\n"
    message += f"<b>Captcha:</b> {data.get('Captcha', '')}\n"
    message += f"<b>Cloudflare:</b> {data.get('Cloudflare', '')}\n"
    message += f"<b>GraphQL:</b> {data.get('GraphQL', '')}\n"
    message += f"<b>Platform:</b> {data.get('Platform', '')}\n"

    # IP Info
    ip_info = data.get('IP Info', {})
    message += f"<b>IP:</b> {ip_info.get('IP', '')}\n"
    message += f"<b>Country:</b> {ip_info.get('Country', '')}\n"
    message += f"<b>ISP:</b> {ip_info.get('ISP', '')}\n"

    # Checked By
    if username:
        message += f"<b>Checked By ~</b> <a href='https://t.me/{username}'>{username}</a>\n"
        message += f"<b>Credits left:</b> {credits_left}"

    return message


# Function to normalize URL
def normalize_url(url):
    parsed_url = urlparse(url)
    if not parsed_url.scheme:
        return 'http://' + url
    return url


# Function to check if a string is a valid URL
def is_valid_url(url):
    parsed_url = urlparse(url)
    return all([parsed_url.scheme, parsed_url.netloc])


# Function to format time in human-readable format
def format_time(seconds):
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"


# Function to handle /redeem command
def redeem(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    if chat_id not in registered_users:
        context.bot.send_message(chat_id=chat_id, text="Kindly register first")
        return

    if len(context.args) != 1:
        context.bot.send_message(
            chat_id=chat_id,
            text="Please provide a valid code.\n/redeem <credit code>")
        return

    code = context.args[0]
    if code in credit_codes:
        credits = credit_codes.pop(code)
        registered_users[chat_id]['credits'] += credits
        save_registered_users()
        context.bot.send_message(
            chat_id=chat_id, text=f"Successfully redeemed {credits} credits")
    else:
        context.bot.send_message(chat_id=chat_id,
                                 text="Invalid code or Already Redeemed.")


# Function to handle /credits command
def credits(update: Update, context: CallbackContext):
    send_credits_info(update.effective_chat.id, context)


# Function to handle /owner command
def owner(update: Update, context: CallbackContext):
    owner_profile = "https://t.me/thewitchleak"
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text=f"Owner profile: {owner_profile}")


# Function to handle /gen_code command
def gen_code(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id

    # Check if user is authorized admin
    if not admin_authorized:
        context.bot.send_message(chat_id=chat_id, text="Unauthorized access")
        return

    # Check if valid arguments are provided
    if len(context.args) != 2:
        context.bot.send_message(
            chat_id=chat_id,
            text="Invalid arguments. Use /gen_code <code> <credits>")
        return

    code, credits = context.args[0], context.args[1]
    try:
        credits = int(credits)
        credit_codes[code] = credits
        context.bot.send_message(
            chat_id=chat_id,
            text=f"Code '{code}' generated with {credits} credits")
    except ValueError:
        context.bot.send_message(chat_id=chat_id, text="Invalid credits value")


# Function to handle /authorize command for admin
def authorize(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id

    # Check if valid arguments are provided
    if len(context.args) != 1:
        context.bot.send_message(
            chat_id=chat_id,
            text="Invalid arguments. Use /authorize <admin_key>")
        return

    admin_key = context.args[0]
    if admin_key == ADMIN_KEY:
        global admin_authorized
        admin_authorized = True
        context.bot.send_message(chat_id=chat_id,
                                 text="Admin privileges granted")
    else:
        context.bot.send_message(chat_id=chat_id, text="Invalid admin key")


# Function to handle /special command
def special(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id

    # Check if valid arguments are provided
    if len(context.args) != 1:
        context.bot.send_message(
            chat_id=chat_id,
            text="Invalid arguments. Use /special <special_key>")
        return

    special_key = context.args[0]
    if special_key == SPECIAL_KEY:
        context.bot.send_message(chat_id=chat_id,
                                 text="Special privileges granted")
    else:
        context.bot.send_message(chat_id=chat_id, text="Invalid special key")


# Load registered users from file
load_registered_users()

# Initialize the bot and dispatcher
updater = Updater(TOKEN, use_context=True)
dispatcher = updater.dispatcher

# Add command handlers to the dispatcher
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("cmds", cmds))
dispatcher.add_handler(CommandHandler("redeem", redeem))
dispatcher.add_handler(CommandHandler("credits", credits))
dispatcher.add_handler(CommandHandler("owner", owner))
dispatcher.add_handler(CommandHandler("gen_code", gen_code))
dispatcher.add_handler(CommandHandler("authorize", authorize))
dispatcher.add_handler(CommandHandler("special", special))
dispatcher.add_handler(CallbackQueryHandler(button_click))

# Add a message handler for text messages
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))

# Start the bot
updater.start_polling()
updater.idle()

if __name__ == '__main__':
    main()
