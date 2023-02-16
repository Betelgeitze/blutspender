from apscheduler.schedulers.blocking import BlockingScheduler
from parser import Parser
from support.manage_db import ManageDB
from support.formatter import Formatter
import json
import os

import telebot
from telebot.apihelper import ApiTelegramException

try:
    with open("config.json") as file:
        config = json.load(file)
except FileNotFoundError:
    with open("../config.json") as file:
        config = json.load(file)

try:
    with open("../support/responses.json") as file:
        rps = json.load(file)
except FileNotFoundError:
    with open("support/responses.json") as file:
        rps = json.load(file)

DELTA = config["delta"]
COUNTRY_CODE = config["country_code"]
TIMEZONE = config["timezone"]
PARSE_HOUR = config["parse_hour"]
PARSE_MIN = config["parse_min"]
APPROXIMATE_MAX_DISTANCE = config["approximate_max_distance"]
MAX_DISTANCE = config["max_distance"]
INFORM_DAYS = config["inform_days"]
SEND_HOUR = config["send_hour"]
SEND_MIN = config["send_min"]

API_KEY = os.environ["BOT_API_KEY"]

parser = Parser(country_code=COUNTRY_CODE)
manage_db = ManageDB(country_code=COUNTRY_CODE)
formatter = Formatter()
bot = telebot.TeleBot(API_KEY)


def run_parser(delta, start_offset_date):
    manage_db.create_tables()
    parser.parse_pages(delta, start_offset_date)
    manage_db.delete_outdated_data()


def send_termine():
    users_with_available_termine = manage_db.check_available_termine(
        approximate_max_distance=APPROXIMATE_MAX_DISTANCE, max_distance=MAX_DISTANCE, inform_days=INFORM_DAYS)
    if not len(users_with_available_termine) == 0:
        for user in users_with_available_termine:
            language = manage_db.get_language(account_id=user["account_id"])
            try:
                bot.send_message(int(user["chat_id"]), rps[language]["appointment_reminder"])
                for termine in user["available_termine"]:
                    for termin in termine:
                        termin_str = formatter.dic_to_string(rps=rps, termin=termin, language=language)
                        bot.send_message(int(user["chat_id"]), termin_str)
            except ApiTelegramException:
                manage_db.delete_user(account_id=user["account_id"])


scheduler = BlockingScheduler(timezone=TIMEZONE)
scheduler.add_job(run_parser, "cron", hour=PARSE_HOUR, minute=PARSE_MIN, args=[DELTA, DELTA])
scheduler.add_job(send_termine, "cron", hour=SEND_HOUR, minute=SEND_MIN)

# Parse 1 week starting from today
print("Running first parser...")
run_parser(DELTA, 0)

scheduler.start()
