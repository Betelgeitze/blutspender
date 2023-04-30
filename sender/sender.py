from support.manage_db import ManageDB
from support.formatter import Formatter

import telebot
from telebot.apihelper import ApiTelegramException
import os
import json

try:
    with open("../support/responses.json") as file:
        rps = json.load(file)
except FileNotFoundError:
    with open("support/responses.json") as file:
        rps = json.load(file)

try:
    with open("config.json") as file:
        config = json.load(file)
except FileNotFoundError:
    with open("../config.json") as file:
        config = json.load(file)

COUNTRY_CODE = config["country_code"]
DISTANCE_DELTA = config["distance_delta"]

API_KEY = os.environ["BOT_API_KEY"]


manage_db = ManageDB(COUNTRY_CODE)
formatter = Formatter()
bot = telebot.TeleBot(API_KEY)


def send_termine():
    users_with_available_termine = manage_db.get_available_termine(DISTANCE_DELTA)
    print(len(users_with_available_termine))
    if not len(users_with_available_termine) == 0:
        for user in users_with_available_termine:
            language = user["selected_language"]
            try:
                bot.send_message(int(user["chat_id"]), rps[language]["appointment_reminder"].format(distance=user["distance"]))
                for termine in user["available_termine"]:
                    for termin in termine:
                        termin_str = formatter.dic_to_string(rps=rps, termin=termin, language=language)
                        bot.send_message(int(user["chat_id"]), termin_str)
            except ApiTelegramException:
                manage_db.delete_user(account_id=user["account_id"])

print("Starting sending...")
send_termine()

# docker build -t betelgeitze/sender -f Dockerfile-sender .
# docker push betelgeitze/sender:latest