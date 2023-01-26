from apscheduler.schedulers.blocking import BlockingScheduler
from parser import Parser
from app.manage_db import ManageDB

DELTA = 2
COUNTRY_CODE = "de"

parser = Parser(country_code=COUNTRY_CODE)
manage_db = ManageDB(country_code=COUNTRY_CODE)


def run_parser(delta, start_offset_date):
    manage_db.create_tables()
    parser.parse_pages(delta, start_offset_date)
    manage_db.delete_outdated_data()


scheduler = BlockingScheduler(timezone="Europe/Berlin")
scheduler.add_job(run_parser, "cron", hour=20, args=[DELTA, DELTA])

# Parse 1 week starting from today
print("Running first parser...")
run_parser(DELTA, 0)

scheduler.start()
