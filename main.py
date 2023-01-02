import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from apscheduler.schedulers.blocking import BlockingScheduler
from threading import Thread
import os
from parser import Parser
from postcode_ranges import PostcodeRanges
from manage_db import ManageDB
from responses import responses as rps

DELTA = 7
START_DATE_OFFSET = 0
# Sends the data 0, 3 and 7 days before
INFORM_DAYS = [0, 3, 7]
APPROXIMATE_MAX_DISTANCE = 20
MAX_DISTANCE = 5
ADD_MIN = 10
FEEDBACK_MIN = 30
API_KEY = os.environ["BOT_API_KEY"]

parser = Parser(DELTA, START_DATE_OFFSET)
postcode_ranges = PostcodeRanges()
manage_db = ManageDB()

bot = telebot.TeleBot(API_KEY)


# SUPPORT FUNCTIONS:
def dic_to_string(termin):
    termin_str = str()
    for key, value in termin.items():
        if key == "Zeiten":
            value = "\n              ".join(value)
        termin_str += f"{key}: {value}\n"
    return termin_str


def get_termine(postcode):
    lat, lon = postcode_ranges.get_lat_and_lon(postcode=postcode)
    min_lat, max_lat, min_lon, max_lon = postcode_ranges.calculate_ranges(APPROXIMATE_MAX_DISTANCE, lat, lon)
    available_termine = manage_db.get_postcodes_nearby(MAX_DISTANCE, postcode, min_lat, max_lat, min_lon, max_lon)
    return available_termine


# SCHEDULED FUNCTIONS
def send_termine():
    users_with_available_termine = manage_db.check_available_termine(
        APPROXIMATE_MAX_DISTANCE=APPROXIMATE_MAX_DISTANCE, MAX_DISTANCE=MAX_DISTANCE, INFORM_DAYS=INFORM_DAYS)
    if not len(users_with_available_termine) == 0:
        for user in users_with_available_termine:
            termin_str = dic_to_string(termin=user["available_termine"])
            bot.send_message(int(user["chat_id"]), termin_str)


def run_parser():
    manage_db.create_tables()
    parser.parse_pages()
    manage_db.delete_outdated_data()

scheduler = BlockingScheduler(timezone="Europe/Berlin")
scheduler.add_job(run_parser, "cron", hour=22)
scheduler.add_job(send_termine, "cron", hour=12)


def schedule_checker():
    while True:
        scheduler.start()


# TO DELETE

# manage_db.delete_tables(["termine", "times", "postcodes", "users", "userpostcodes"])
# run_parser()
# print("test")


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

def add_in_db_and_reply(message, language):
    postcode = message.text.strip()
    account_id = message.from_user.id
    chat_id = message.chat.id

    if postcode.isdigit() and len(postcode) == 5:
        manage_db.insert_user_postcodes(account_id=account_id, text=postcode)
        available_termine = get_termine(postcode=postcode)
        if len(available_termine) == 0:
            bot.send_message(chat_id,
                             rps[language]["no_termine"] +
                             rps[language]["no_action"] +
                             rps[language]["add_or_del"])
        else:
            for termin in available_termine:
                termin_str = dic_to_string(termin)
                bot.send_message(chat_id,
                                 rps[language]["yes_termine"] +
                                 rps[language]["no_action"] +
                                 rps[language]["add_or_del"])
                bot.send_message(chat_id,
                                 termin_str)
    else:
        bot.send_message(chat_id,
                         rps[language]["wrong_postcode"])


def change_language(callback_query, language):
    postcode_exists = manage_db.get_user_postcodes(callback_query.from_user.id)[0]
    if not postcode_exists:
        bot.reply_to(callback_query.message,
                     rps[language]["welcome_msg"] +
                     rps[language]["write_postcode"])
    else:
        bot.reply_to(callback_query.message,
                     rps[language]["language_changed"] +
                     rps[language]["add_or_del"])


def remind_time(account_id, chat_id, language):
    remind_date = manage_db.want_remind(account_id=account_id)[1]
    bot.send_message(chat_id,
                     rps[language]["reminder_success"].format(remind_date))


# BOT RUNNING

@bot.message_handler(commands=['start', 'help'])
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
                             rps[language]["no_action_required"] +
                             rps[language]["add_example"],
                             reply_markup=main_keyboard)
            else:
                bot.reply_to(message,
                             rps[language]["welcome_msg"] +
                             rps[language]["no_action_required"] +
                             rps[language]["not_reminding"].format(remind_date),
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
                                 rps[language]["postcode_not_exist"].format(command))
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
                             rps[language]["no_action_info"] +
                             rps[language]["add_or_del"])
            else:
                bot.send_message(chat_id,
                                 rps[language]["no_action_required"] +
                                 rps[language]["not_reminding"] +
                                 rps[language]["not_reminding"])
        else:
            add_in_db_and_reply(message, language)

        manage_db.update_timers(account_id=account_id, open=False, timer="postcode_timer")
        manage_db.update_timers(account_id=account_id, open=False, timer="feedback_timer")


@bot.callback_query_handler(func=lambda query: True)
def handle_callback_query(callback_query):
    data = callback_query.data
    account_id = callback_query.from_user.id
    chat_id = callback_query.message.chat.id
    message_id = callback_query.message.message_id

    manage_db.update_timers(account_id, False, "postcode_timer")

    if not callback_query.from_user.is_bot:
        language = manage_db.get_language(account_id=account_id)

        if data == 'english_btn_clicked':
            manage_db.update_language(account_id=account_id, language="en")
            change_language(callback_query=callback_query, language="en")
        elif data == 'deutsch_btn_clicked':
            manage_db.update_language(account_id=account_id, language="de")
            change_language(callback_query=callback_query, language="de")

        elif data == 'change_language_btn_clicked':
            language_keyboard = create_language_keyboard()
            bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                  text=rps["select_language"],
                                  reply_markup=language_keyboard)

        elif data == 'add_btn_clicked':
            manage_db.update_timers(account_id=account_id, open=True, timer="postcode_timer", minutes=ADD_MIN)
            bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                  text=rps[language]["write_postcode"])
        elif data == 'show_btn_clicked':
            user_postcodes = manage_db.get_user_postcodes(account_id=account_id)[1]
            user_postcodes_str = "\n".join(user_postcodes)
            bot.send_message(chat_id, rps[language]["available_postcodes"] + user_postcodes_str)
        elif data == 'delete_btn_clicked':
            bot.reply_to(callback_query.message, rps[language]["del_example"])

        elif data == 'feedback_btn_clicked':
            bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                  text=rps[language]["write_feedback"])
            manage_db.update_timers(account_id=account_id, open=True, timer="feedback_timer", minutes=FEEDBACK_MIN)

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
                                  text=rps[language]["else_stop_feedback"] + rps[language]["reminder_length"],
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
                                  text=rps[language]["welcome_msg"] + rps[language]["no_action_required"] +
                                       rps[language]["add_example"],
                                  reply_markup=main_keyboard)


# LOOPING
Thread(target=schedule_checker).start()
bot.polling()
