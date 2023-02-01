from apscheduler.schedulers.blocking import BlockingScheduler
from parser import Parser
from support.manage_db import ManageDB
import json

try:
    with open("config.json") as file:
        config = json.load(file)
except FileNotFoundError:
    with open("../config.json") as file:
        config = json.load(file)

DELTA = config["delta"]
COUNTRY_CODE = config["country_code"]
TIMEZONE = config["timezone"]
PARSE_HOUR = config["parse_hour"]
PARSE_MIN = config["parse_min"]

parser = Parser(country_code=COUNTRY_CODE)
manage_db = ManageDB(country_code=COUNTRY_CODE)


def run_parser(delta, start_offset_date):
    manage_db.create_tables()
    parser.parse_pages(delta, start_offset_date)
    manage_db.delete_outdated_data()


scheduler = BlockingScheduler(timezone=TIMEZONE)
scheduler.add_job(run_parser, "cron", hour=PARSE_HOUR, minute=PARSE_MIN, args=[DELTA, DELTA])

# Delete DB Tables if needed
manage_db.delete_tables(["feedback","postcodes","termine", "times", "userpostcodes", "users"])

# Parse 1 week starting from today
print("Running first parser...")
run_parser(DELTA, 0)

scheduler.start()
