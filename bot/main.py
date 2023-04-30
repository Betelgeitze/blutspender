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
DEFAULT_LANGUAGE = config["default_language"]
MAX_DISTANCE = config["max_distance"]
DEFAULT_DISTANCE = config["default_distance"]
DISTANCE_DELTA = config["distance_delta"]
INFORM_DAYS = config["inform_days"]
DELTA = config["delta"]
REMINDER_DAYS = config["reminder_days"]

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
def create_main_keyboard(language):
    main_keyboard = InlineKeyboardMarkup()
    add_postcode_btn = InlineKeyboardButton(text=rps[language]["keyboard_add"],
                                            callback_data="add_btn_clicked")
    show_postcodes_btn = InlineKeyboardButton(text=rps[language]["keyboard_show"],
                                              callback_data="show_btn_clicked")
    delete_postcodes_btn = InlineKeyboardButton(text=rps[language]["keyboard_del"],
                                                callback_data="delete_btn_clicked")
    feedback_btn = InlineKeyboardButton(text=rps[language]["feedback"],
                                        callback_data="feedback_btn_clicked")
    settings = InlineKeyboardButton(text=rps[language]["settings"],
                                    callback_data="settings_btn_clicked")
    main_keyboard.row(add_postcode_btn)
    main_keyboard.row(show_postcodes_btn)
    main_keyboard.row(delete_postcodes_btn)
    main_keyboard.row(feedback_btn)
    main_keyboard.row(settings)

    return main_keyboard


def create_language_keyboard():
    language_keyboard = InlineKeyboardMarkup()
    english_btn = InlineKeyboardButton(text="English",
                                       callback_data="english_btn_clicked")
    deutsch_btn = InlineKeyboardButton(text="Deutsch",
                                       callback_data="deutsch_btn_clicked")
    language_keyboard.add(english_btn, deutsch_btn)
    return language_keyboard


def create_settings_keyboard(language, remind):
    settings_keyboard = InlineKeyboardMarkup()

    change_distance_btn = InlineKeyboardButton(text=rps[language]["distance"],
                                               callback_data="distance_btn_clicked")

    change_reminder_days_btn = InlineKeyboardButton(text=rps[language]["reminder_days"],
                                                    callback_data="reminder_days_btn_clicked")

    change_language_btn = InlineKeyboardButton(text=rps[language]["change_language"],
                                               callback_data="change_language_btn_clicked")
    if remind:
        reminder = InlineKeyboardButton(text=rps[language]["reminder"],
                                        callback_data="reminder_btn_clicked")
    else:
        reminder = InlineKeyboardButton(text=rps[language]["remind_again"],
                                        callback_data="remind_again_btn_clicked")
    settings_keyboard.row(change_distance_btn)
    settings_keyboard.row(change_reminder_days_btn)
    settings_keyboard.row(reminder)
    settings_keyboard.row(change_language_btn)

    return settings_keyboard


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

def msg(reply, account_id, responses, ktype=None, message=None, command=None):
    text = ""
    zero_days = ""
    non_zero_days = ""
    _and = ""

    user = manage_db.get_user_data(account_id=account_id)
    remind, remind_date = manage_db.check_if_remind(account_id=account_id)
    days = manage_db.get_reminder_days(account_id=account_id)

    main_keyboard = create_main_keyboard(language=user.selected_language)
    language_keyboard = create_language_keyboard()
    settings_keyboard = create_settings_keyboard(language=user.selected_language, remind=remind)
    stop_reminder_reason_keyboard = create_stop_reminder_reason_keyboard(language=user.selected_language)
    stop_reminder_length_keyboard = create_stop_reminder_length_keyboard(language=user.selected_language)

    keyboards = {
        "main": main_keyboard,
        "lang": language_keyboard,
        "settings": settings_keyboard,
        "reason": stop_reminder_reason_keyboard,
        "length": stop_reminder_length_keyboard,
        None: None
    }

    # Dealing with "no_action_info" response
    if 0 in days:
        zero_days = rps[user.selected_language]["zero_days"]
        if len(days) > 1:
            if len(days) == 2 and 1 in days:
                plural = ""
            else:
                plural = rps[user.selected_language]["plural"]
            _and = rps[user.selected_language]["_and"]
            non_zero_days = rps[user.selected_language]["non_zero_days"].format(plural=plural)
        days.remove(0)
    else:
        if len(days) == 1 and 1 in days:
            plural = ""
        else:
            plural = rps[user.selected_language]["plural"]
        non_zero_days = rps[user.selected_language]["non_zero_days"].format(plural=plural)

    days = ", ".join(map(str, days))

    # Unpacking responses
    for response in responses:
        try:
            text = text + rps[user.selected_language][response]
        except KeyError:
            text = text + response
    filled_text = text.format(
        distance=user.distance,
        max_distance=MAX_DISTANCE,
        days=days,
        non_zero_days=non_zero_days,
        zero_days=zero_days,
        _and=_and,
        remind_date=remind_date,
        postcode=command,
        delta=DELTA
    )

    match reply:
        case "send":
            return bot.send_message(
                chat_id=user.chat_id,
                text=filled_text,
                reply_markup=keyboards[ktype]
            )
        case "reply":
            return bot.reply_to(
                message=message,
                text=filled_text,
                reply_markup=keyboards[ktype]
            )
        case "edit":
            return bot.edit_message_text(
                chat_id=user.chat_id,
                message_id=message.id,
                text=filled_text,
                reply_markup=keyboards[ktype]
            )


def get_termine(postcode, distance):
    lat, lon = postcode_ranges.get_lat_and_lon(postcode=postcode)
    min_lat, max_lat, min_lon, max_lon = postcode_ranges.calculate_ranges(distance + DISTANCE_DELTA, lat, lon)
    available_termine = manage_db.get_postcodes_nearby(distance, postcode, min_lat, max_lat, min_lon, max_lon,
                                                       inform_days=None)
    return available_termine


def change_language(callback_query, account_id):
    postcode_exists = manage_db.get_user_postcodes(callback_query.from_user.id)
    if not postcode_exists:
        msg("reply", account_id, ["no_action_info", "write_postcode"], message=callback_query.message)
    else:
        msg("reply", account_id, ["language_changed", "add_or_del"], message=callback_query.message)


print("Bot is running")


# BOT RUNNING

@bot.message_handler(commands=['start', 'help', 'menu'])
def welcome_message(message):
    if not message.from_user.is_bot:
        account_id = message.from_user.id
        user_data = message.json
        manage_db.insert_users(user_data=user_data, default_distance=DEFAULT_DISTANCE, default_language=DEFAULT_LANGUAGE)

        postcode_exists = manage_db.get_user_postcodes(account_id=account_id)
        remind, remind_date = manage_db.check_if_remind(account_id=account_id)

        if postcode_exists:
            if remind:
                msg("send", account_id, ["no_action_info", "no_action_required", "add_example"], ktype="main")
            else:
                msg("send", account_id, ["no_action_info", "no_action_required", "not_reminding", "use_interface"],
                    ktype="main")
        else:
            msg("send", account_id, ["select_language"], ktype="lang")


@bot.message_handler()
def send_postcode(message):
    if not message.from_user.is_bot:
        account_id = message.from_user.id
        text = message.text.strip()

        user = manage_db.get_user_data(account_id=account_id)
        response = user.response

        remind, remind_date = manage_db.check_if_remind(account_id=account_id)
        postcode_exists = manage_db.get_user_postcodes(account_id=account_id)

        if "delete:" in text.lower():
            command = text.split(":")
            command = [c.strip() for c in command][1]
            if len(command) > 1:
                postcode_row = manage_db.delete_user_postcode(account_id=account_id, command=command)
                postcode_exists = manage_db.get_user_postcodes(account_id=account_id)

                if postcode_row is None:
                    msg("reply", account_id, ["wrong_postcode", "show_all"], message=message)
                else:
                    msg("reply", account_id, ["del_success"], message=message, command=command)
                    if postcode_exists:
                        msg("reply", account_id, ["add_or_del"], message=message)
                    else:
                        msg("reply", account_id, ["reset"], message=message)
                        welcome_message(message)
            else:
                msg("reply", account_id, ["failed_del", "del_example"], message=message)
        elif response == "postcode" or not postcode_exists:
            searcher = msg("send", account_id, ["await"])
            # Checking against pgeocode if a postcode exists in reality
            lat = postcode_ranges.get_lat_and_lon(text)[0]

            if not math.isnan(lat):
                manage_db.insert_user_postcodes(account_id=account_id, text=text)
                available_termine = get_termine(postcode=text, distance=user.distance)
                if len(available_termine) == 0:
                    msg("edit", account_id, ["no_termine", "no_action_info", "no_action"], message=searcher)
                else:
                    msg("edit", account_id, ["yes_termine", "no_action_info", "no_action"], message=searcher)
                    for termin in available_termine:
                        termin_str = formatter.dic_to_string(rps, termin, user.selected_language)
                        msg("send", account_id, termin_str)
                msg("send", account_id, ["add_or_del"])
            else:
                msg("edit", account_id, ["wrong_postcode", "write_start"], message=searcher)
        elif response == "feedback":
            manage_db.insert_feedback(account_id, text)
            msg("reply", account_id, ["feedback_thanks"], message=message)
            welcome_message(message)
        elif response == "distance":
            dist = text.replace(",", ".")
            try:
                dist = float(dist)
                if 0 <= dist <= MAX_DISTANCE:
                    manage_db.update_user(account_id, "distance", dist)
                    msg("reply", account_id, ["distance_success"], message=message)
                    welcome_message(message)
                else:
                    msg("reply", account_id, ["big_digit"], message=message)
                    welcome_message(message)
            except ValueError:
                msg("reply", account_id, ["enter_digit"], message=message)
                welcome_message(message)
        elif response == "days":
            command = text.split(",")
            command = [c.strip() for c in command]
            command = [int(c) for c in command if c.isdigit() and 0 <= int(c) < DELTA]
            if len(command) > 0:
                manage_db.insert_reminder_days(account_id, command)
                msg("reply", account_id, ["days_changed"], message=message)
                welcome_message(message)
            else:
                msg("reply", account_id, ["wrong_days_format", "write_start"], message=message)
        elif remind:
            msg("send", account_id, ["no_action_required", "no_action_info", "add_or_del"])
        else:
            msg("send", account_id, ["no_action_required", "not_reminding", "add_or_del"])

        manage_db.update_user(account_id, "response", "none")


@bot.callback_query_handler(func=lambda query: True)
def handle_callback_query(callback_query):
    data = callback_query.data
    account_id = callback_query.from_user.id
    message = callback_query.message
    user = manage_db.get_user_data(account_id)

    # Checking if the user is in database
    if user is not None:

        if not callback_query.from_user.is_bot:
            # I add this exception handler because without it if you click a button which edits the message very fast,
            # it will tell you that it cannot substitute the message with the identical message and through an error.
            # I could not find a better solution. It seems to be a Telegram problem according to:
            # https://stackoverflow.com/questions/60862027/telegram-bot-with-python-telegram-error-badrequest-message-is-not-modified
            try:
                match data:
                    case "english_btn_clicked":
                        manage_db.update_user(account_id, "selected_language", "en")
                        change_language(callback_query, account_id)
                    case 'deutsch_btn_clicked':
                        manage_db.update_user(account_id, "selected_language", "de")
                        change_language(callback_query, account_id)

                    case 'change_language_btn_clicked':
                        msg("send", account_id, ["select_language"], ktype="lang")

                    case 'add_btn_clicked':
                        manage_db.update_user(account_id, "response", "postcode")
                        msg("send", account_id, ["write_postcode"])

                    case 'show_btn_clicked':
                        user_postcodes = manage_db.get_user_postcodes(account_id=account_id)
                        user_postcodes_str = "\n".join(user_postcodes)
                        msg("send", account_id, ["available_postcodes", user_postcodes_str])

                    case 'delete_btn_clicked':
                        msg("send", account_id, ["del_example"])

                    case 'feedback_btn_clicked':
                        manage_db.update_user(account_id, "response", "feedback")
                        msg("send", account_id, ["write_feedback"])

                    case "settings_btn_clicked":
                        msg("edit", account_id, ["settings_explanation"], message=message, ktype="settings")

                    case "distance_btn_clicked":
                        manage_db.update_user(account_id, "response", "distance")
                        msg("edit", account_id, ["distance_explanation"], message=message)

                    case "reminder_days_btn_clicked":
                        manage_db.update_user(account_id, "response", "days")
                        msg("edit", account_id, ["reminder_days_input", "reminder_days_example"], message=message)

                    case "reminder_btn_clicked":
                        msg("edit", account_id, ["stop_reminder_reason"], message=message, ktype="reason")

                    case "donated_btn_clicked":
                        manage_db.addup_donations(account_id=account_id)
                        msg("edit", account_id, ["reminder_length"], ktype="length",
                            message=message)

                    case "often_btn_clicked":
                        text = "ADMIN: Too often"
                        manage_db.insert_feedback(account_id=account_id, text=text)
                        msg("edit", account_id, ["reminder_length"], ktype="length",
                            message=message)

                    case "else_btn_clicked":
                        text = "ADMIN: Else"
                        manage_db.insert_feedback(account_id=account_id, text=text)
                        msg("edit", account_id, ["else_stop_feedback", "reminder_length"], ktype="length",
                            message=message)

                    case "remind_one_week_btn_clicked":
                        manage_db.update_user(account_id, "start_reminding", REMINDER_DAYS[1])
                        msg("send", account_id, ["reminder_success"])

                    case "remind_two_months_btn_clicked":
                        manage_db.update_user(account_id, "start_reminding", REMINDER_DAYS[2])
                        msg("send", account_id, ["reminder_success"])

                    case "remind_six_months_btn_clicked":
                        manage_db.update_user(account_id, "start_reminding", REMINDER_DAYS[3])
                        msg("send", account_id, ["reminder_success"])

                    case "remind_again_btn_clicked":
                        manage_db.update_user(account_id, "start_reminding", REMINDER_DAYS[0])
                        msg("edit", account_id, ["no_action_info", "no_action_required", "add_example"], ktype="main",
                            message=message)
            except ApiTelegramException:
                print("ApiTelegramException")


# LOOPING
bot.infinity_polling()

# docker build -t betelgeitze/bot -f Dockerfile-bot .
# docker push betelgeitze/bot:latest
