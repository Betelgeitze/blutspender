import json
import math
import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telebot.apihelper import ApiTelegramException

from support.postcode_ranges import PostcodeRanges
from support.manage_db import ManageDB
from support.formatter import Formatter

with open("config.json") as file:
    config = json.load(file)

COUNTRY_CODE = config["country_code"]
INFORM_DAYS = config["inform_days"]
APPROXIMATE_MAX_DISTANCE = config["approximate_max_distance"]
MAX_DISTANCE = config["max_distance"]
ADD_TIMEOUT = config["add_timeout"]
FEEDBACK_TIMEOUT = config["feedback_timeout"]

API_KEY = os.environ["BOT_API_KEY"]

try:
    with open("../support/responses.json") as file:
        rps = json.load(file)
except FileNotFoundError:
    with open("support/responses.json") as file:
        rps = json.load(file)

postcode_ranges = PostcodeRanges(country_code=COUNTRY_CODE)
manage_db = ManageDB(country_code=COUNTRY_CODE)
formatter = Formatter()
bot = telebot.TeleBot(API_KEY)


# Keyboards
def create_main_keyboard(language, remind):
    main_keyboard = InlineKeyboardMarkup()

    add_postcode_btn = InlineKeyboardButton(text=rps[language]["keyboard_add"],
                                            callback_data="add_btn_clicked")
    show_postcodes_btn = InlineKeyboardButton(text=rps[language]["keyboard_show"],
                                              callback_data="show_btn_clicked")
    delete_postcodes_btn = InlineKeyboardButton(text=rps[language]["keyboard_del"],
                                                callback_data="delete_btn_clicked")
    change_language_btn = InlineKeyboardButton(text=rps[language]["change_language"],
                                               callback_data="change_language_btn_clicked")
    feedback_btn = InlineKeyboardButton(text=rps[language]["feedback"],
                                        callback_data="feedback_btn_clicked")
    if remind:
        reminder = InlineKeyboardButton(text=rps[language]["reminder"],
                                        callback_data="reminder_btn_clicked")
    else:
        reminder = InlineKeyboardButton(text=rps[language]["remind_again"],
                                        callback_data="remind_again_btn_clicked")

    main_keyboard.row(add_postcode_btn)
    main_keyboard.row(show_postcodes_btn)
    main_keyboard.row(delete_postcodes_btn)
    main_keyboard.row(change_language_btn)
    main_keyboard.row(feedback_btn)
    main_keyboard.row(reminder)

    return main_keyboard


def create_language_keyboard():
    language_keyboard = InlineKeyboardMarkup()
    english_btn = InlineKeyboardButton(text="English",
                                       callback_data="english_btn_clicked")
    deutsch_btn = InlineKeyboardButton(text="Deutsch",
                                       callback_data="deutsch_btn_clicked")
    language_keyboard.add(english_btn, deutsch_btn)
    return language_keyboard


def create_stop_reminder_reason_keyboard(language):
    stop_reminder_reason_keyboard = InlineKeyboardMarkup()
    donated_stop_reminder = InlineKeyboardButton(text=rps[language]["donated_stop_reminder"],
                                                 callback_data="donated_btn_clicked")
    often_stop_reminder = InlineKeyboardButton(text=rps[language]["often_stop_reminder"],
                                               callback_data="often_btn_clicked")
    else_stop_reminder = InlineKeyboardButton(text=rps[language]["else_stop_reminder"],
                                              callback_data="else_btn_clicked")
    stop_reminder_reason_keyboard.row(donated_stop_reminder)
    stop_reminder_reason_keyboard.row(often_stop_reminder)
    stop_reminder_reason_keyboard.row(else_stop_reminder)
    return stop_reminder_reason_keyboard


def create_stop_reminder_length_keyboard(language):
    stop_reminder_length_keyboard = InlineKeyboardMarkup()

    remind_one_week = InlineKeyboardButton(text=rps[language]["remind_one_week"],
                                           callback_data="remind_one_week_btn_clicked")
    remind_two_months = InlineKeyboardButton(text=rps[language]["remind_two_months"],
                                             callback_data="remind_two_months_btn_clicked")
    remind_six_months = InlineKeyboardButton(text=rps[language]["remind_six_months"],
                                             callback_data="remind_six_months_btn_clicked")
    stop_reminder_length_keyboard.row(remind_one_week)
    stop_reminder_length_keyboard.row(remind_two_months)
    stop_reminder_length_keyboard.row(remind_six_months)
    return stop_reminder_length_keyboard


# Support functions
def get_termine(postcode):
    lat, lon = postcode_ranges.get_lat_and_lon(postcode=postcode)
    min_lat, max_lat, min_lon, max_lon = postcode_ranges.calculate_ranges(APPROXIMATE_MAX_DISTANCE, lat, lon)
    available_termine = manage_db.get_postcodes_nearby(MAX_DISTANCE, postcode, min_lat, max_lat, min_lon, max_lon,
                                                       inform_days=None)
    return available_termine


def add_in_db_and_reply(message, language):
    postcode = message.text.strip()
    account_id = message.from_user.id
    chat_id = message.chat.id

    # Checking against pgeocode if a postcode exists in reality
    lat = postcode_ranges.get_lat_and_lon(postcode)[0]

    if not math.isnan(lat):
        manage_db.insert_user_postcodes(account_id=account_id, text=postcode)
        available_termine = get_termine(postcode=postcode)
        if len(available_termine) == 0:
            bot.send_message(chat_id,
                             rps[language]["no_termine"] +
                             rps[language]["no_action_info"].format(config["inform_days"][-1]) +
                             rps[language]["no_action"] +
                             rps[language]["add_or_del"])
        else:
            bot.send_message(chat_id,
                             rps[language]["yes_termine"] +
                             rps[language]["no_action_info"].format(config["inform_days"][-1]) +
                             rps[language]["no_action"])
            for termin in available_termine:
                termin_str = formatter.dic_to_string(rps, termin, language)

                bot.send_message(chat_id,
                                 termin_str)
            bot.send_message(chat_id,
                             rps[language]["add_or_del"])
    else:
        bot.send_message(chat_id,
                         rps[language]["wrong_postcode"] +
                         rps[language]["write_start"])


def change_language(callback_query, language):
    postcode_exists = manage_db.get_user_postcodes(callback_query.from_user.id)[0]
    if not postcode_exists:
        bot.reply_to(callback_query.message,
                     rps[language]["welcome_msg"] +
                     rps[language]["no_action_info"].format(config["inform_days"][-1], config["inform_days"][-2]) +
                     rps[language]["write_postcode"])
    else:
        bot.reply_to(callback_query.message,
                     rps[language]["language_changed"] +
                     rps[language]["add_or_del"])


def remind_time(account_id, chat_id, language):
    remind_date = manage_db.want_remind(account_id=account_id)[1]
    bot.send_message(chat_id,
                     rps[language]["reminder_success"].format(remind_date))


print("Bot is running")


# BOT RUNNING

@bot.message_handler(commands=['start', 'help', 'menu'])
def welcome_message(message):
    if not message.from_user.is_bot:
        account_id = message.from_user.id
        user_data = message.json

        manage_db.insert_users(user_data=user_data)
        postcode_exists = manage_db.get_user_postcodes(account_id=account_id)[0]

        remind, remind_date = manage_db.want_remind(account_id=account_id)

        language = manage_db.get_language(account_id=account_id)
        main_keyboard = create_main_keyboard(language=language, remind=remind)
        language_keyboard = create_language_keyboard()

        if postcode_exists:
            if remind:
                bot.reply_to(message,
                             rps[language]["welcome_msg"] +
                             rps[language]["no_action_info"].format(config["inform_days"][-1],
                                                                    config["inform_days"][-2]) +
                             rps[language]["no_action_required"] +
                             rps[language]["add_example"],
                             reply_markup=main_keyboard)
            else:
                bot.reply_to(message,
                             rps[language]["welcome_msg"] +
                             rps[language]["no_action_info"].format(config["inform_days"][-1],
                                                                    config["inform_days"][-2]) +
                             rps[language]["no_action_required"] +
                             rps[language]["not_reminding"].format(remind_date) +
                             rps[language]["use_interface"],
                             reply_markup=main_keyboard)
        else:
            bot.reply_to(message,
                         rps["select_language"],
                         reply_markup=language_keyboard)


@bot.message_handler()
def send_postcode(message):
    if not message.from_user.is_bot:
        account_id = message.from_user.id
        chat_id = message.chat.id
        text = message.text

        add_another_postcode = manage_db.check_timers(account_id=account_id, timer="postcode_timer")
        add_feedback = manage_db.check_timers(account_id=account_id, timer="feedback_timer")
        postcode_exists = manage_db.get_user_postcodes(account_id=account_id)[0]
        remind, remind_date = manage_db.want_remind(account_id=account_id)
        language = manage_db.get_language(account_id=account_id)

        if "delete:" in text.lower():
            command = text.split(":")
            command = [c.strip() for c in command][1]
            if len(command) > 1:
                postcode_row = manage_db.delete_user_postcode(account_id=account_id, command=command)
                postcode_exists = manage_db.get_user_postcodes(account_id=account_id)[0]
                if postcode_row is None:
                    bot.reply_to(message,
                                 rps[language]["wrong_postcode"] +
                                 rps[language]["show_all"])
                else:
                    bot.reply_to(message,
                                 rps[language]["del_success"].format(command))
                    if postcode_exists:
                        bot.reply_to(message,
                                     rps[language]["add_or_del"])
                    else:
                        bot.reply_to(message,
                                     rps[language]["reset"])
                        welcome_message(message)
            else:
                bot.reply_to(message,
                             rps[language]["failed_del"] +
                             rps[language]["del_example"])
        elif add_another_postcode:
            bot.send_message(chat_id,
                             rps[language]["await"])
            add_in_db_and_reply(message, language)
        elif add_feedback:
            manage_db.insert_feedback(account_id=account_id, text=text)
            bot.reply_to(message,
                         rps[language]["feedback_thanks"])
            welcome_message(message)
        elif postcode_exists:
            if remind:
                bot.send_message(chat_id,
                                 rps[language]["no_action_required"] +
                                 rps[language]["no_action_info"].format(config["inform_days"][-1],
                                                                        config["inform_days"][-2]) +
                                 rps[language]["add_or_del"])
            else:
                bot.send_message(chat_id,
                                 rps[language]["no_action_required"] +
                                 rps[language]["not_reminding"].format(remind_date) +
                                 rps[language]["add_or_del"])
        else:
            bot.send_message(chat_id,
                             rps[language]["await"])
            add_in_db_and_reply(message, language)

        manage_db.update_timers(account_id=account_id, open=False, timer="postcode_timer")
        manage_db.update_timers(account_id=account_id, open=False, timer="feedback_timer")


@bot.callback_query_handler(func=lambda query: True)
def handle_callback_query(callback_query):
    data = callback_query.data
    account_id = callback_query.from_user.id
    chat_id = callback_query.message.chat.id
    message_id = callback_query.message.message_id

    # Checking if the user is in database
    user, session = manage_db.get_user(account_id)
    manage_db.close_session(session)
    if user is not None:
        manage_db.update_timers(account_id, False, "postcode_timer")

        if not callback_query.from_user.is_bot:
            # I add this exception handler because without it if you click a button which edits the message very fast,
            # it will tell you that it cannot substitute the message with the identical message and through an error.
            # I could not find a better solution. It seems to be a Telegram problem according to:
            # https://stackoverflow.com/questions/60862027/telegram-bot-with-python-telegram-error-badrequest-message-is-not-modified
            try:
                language = manage_db.get_language(account_id=account_id)

                if data == 'english_btn_clicked':
                    manage_db.update_language(account_id=account_id, language="en")
                    change_language(callback_query=callback_query, language="en")
                elif data == 'deutsch_btn_clicked':
                    manage_db.update_language(account_id=account_id, language="de")
                    change_language(callback_query=callback_query, language="de")

                elif data == 'change_language_btn_clicked':
                    language_keyboard = create_language_keyboard()
                    bot.send_message(chat_id=chat_id,
                                     text=rps["select_language"],
                                     reply_markup=language_keyboard)

                elif data == 'add_btn_clicked':
                    manage_db.update_timers(account_id=account_id, open=True, timer="postcode_timer", minutes=ADD_TIMEOUT)
                    bot.send_message(chat_id=chat_id,
                                     text=rps[language]["write_postcode"])
                elif data == 'show_btn_clicked':
                    user_postcodes = manage_db.get_user_postcodes(account_id=account_id)[1]
                    user_postcodes_str = "\n".join(user_postcodes)
                    bot.send_message(chat_id, rps[language]["available_postcodes"] + user_postcodes_str)
                elif data == 'delete_btn_clicked':
                    bot.reply_to(callback_query.message, rps[language]["del_example"])

                elif data == 'feedback_btn_clicked':
                    bot.send_message(chat_id=chat_id,
                                     text=rps[language]["write_feedback"])
                    manage_db.update_timers(account_id=account_id, open=True, timer="feedback_timer",
                                            minutes=FEEDBACK_TIMEOUT)

                elif data == "reminder_btn_clicked":
                    stop_reminder_reason_keyboard = create_stop_reminder_reason_keyboard(language=language)
                    bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                          text=rps[language]["stop_reminder_reason"],
                                          reply_markup=stop_reminder_reason_keyboard)

                elif data == "donated_btn_clicked":
                    manage_db.addup_donations(account_id=account_id)
                    stop_reminder_length_keyboard = create_stop_reminder_length_keyboard(language=language)
                    bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                          text=rps[language]["reminder_length"],
                                          reply_markup=stop_reminder_length_keyboard)

                elif data == "often_btn_clicked":
                    text = "ADMIN: Too often"
                    manage_db.insert_feedback(account_id=account_id, text=text)
                    stop_reminder_length_keyboard = create_stop_reminder_length_keyboard(language=language)
                    bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                          text=rps[language]["reminder_length"],
                                          reply_markup=stop_reminder_length_keyboard)
                elif data == "else_btn_clicked":
                    text = "ADMIN: Else"
                    manage_db.insert_feedback(account_id=account_id, text=text)
                    stop_reminder_length_keyboard = create_stop_reminder_length_keyboard(language=language)
                    bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                          text=rps[language]["else_stop_feedback"] +
                                               rps[language]["reminder_length"],
                                          reply_markup=stop_reminder_length_keyboard)

                elif data == "remind_one_week_btn_clicked":
                    manage_db.remind_in(account_id=account_id, days=7)
                    remind_time(account_id=account_id, chat_id=chat_id, language=language)

                elif data == "remind_two_months_btn_clicked":
                    manage_db.remind_in(account_id=account_id, days=56)
                    remind_time(account_id=account_id, chat_id=chat_id, language=language)

                elif data == "remind_six_months_btn_clicked":
                    manage_db.remind_in(account_id=account_id, days=168)
                    remind_time(account_id=account_id, chat_id=chat_id, language=language)

                elif data == "remind_again_btn_clicked":
                    manage_db.remind_in(account_id=account_id, days=0)
                    remind = manage_db.want_remind(account_id=account_id)[0]
                    main_keyboard = create_main_keyboard(language=language, remind=remind)
                    bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                          text=rps[language]["welcome_msg"] +
                                               rps[language]["no_action_info"].format(config["inform_days"][-1],
                                                                                      config["inform_days"][-2]) +
                                               rps[language]["no_action_required"] +
                                               rps[language]["add_example"],
                                          reply_markup=main_keyboard)
            except ApiTelegramException:
                print("ApiTelegramException")


# LOOPING
bot.infinity_polling()

# docker build -t betelgeitze/bot -f Dockerfile-bot .
# docker push betelgeitze/bot:latest