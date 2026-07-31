from datetime import datetime
import requests
from bs4 import BeautifulSoup
from time import sleep
import random
from support.manage_db import ManageDB
from support.date_manager import DateManager
import json

with open("config.json") as file:
    config = json.load(file)

DELTA = config["delta"]
OFFSET = config["offset"]
COUNTRY_CODE = config["country_code"]

manage_db = ManageDB(COUNTRY_CODE)
date_manager = DateManager()

# The DRK search endpoint is slow and stalls past the read timeout often enough
# to matter: cron fires this once a day, unattended, and without retries a single
# bad page out of dozens discards the entire run.
RETRIES = 4
BACKOFF_BASE = 3

# Runaway guard. The loop below ends only when it finds the end-of-results alert,
# so if DRK ever renames that CSS class it would page through their site forever.
# A real 9-day window is a few dozen pages; 500 is far above anything legitimate.
MAX_PAGES = 500


def fetch_page(page_url):
    """GET one result page, retrying transient failures with backoff.

    Raises the last exception once the attempts are used up — a site that is
    still failing after this is genuinely down, and failing loudly is what makes
    run-job.sh alert ADMIN_CHAT_ID instead of silently parsing nothing.
    """
    for attempt in range(1, RETRIES + 1):
        try:
            # Always time out: a stalled connection with no timeout hangs
            # forever, so tomorrow's run stacks on top of today's.
            response = requests.get(url=page_url, timeout=(10, 30))
            # A 5xx returns HTML that parses to zero cards and no end-of-results
            # alert, which would otherwise look like an ordinary empty page.
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            if attempt == RETRIES:
                raise
            # Jitter so repeated attempts do not line up with whatever made the
            # site slow to begin with.
            wait = BACKOFF_BASE * 2 ** (attempt - 1) + random.uniform(0, 1)
            print(f"Page request failed ({type(e).__name__}), "
                  f"retrying in {wait:.1f}s [{attempt}/{RETRIES - 1}]")
            sleep(wait)


def parse_pages(delta, start_date_offset):
    # Getting times
    offsetted_today, days_later = date_manager.get_time_range(delta, start_date_offset)
    print(f"Parsing appointements from {offsetted_today} - {days_later}")

    # Parsing DRK
    next_page = True
    counter = 0
    while next_page:
        counter += 1

        # Random Delay
        delay = random.uniform(0, 2)
        sleep(delay)

        page_url = f"https://www.drk-blutspende.de/blutspendetermine/termine?button=&county_id=&date_from={offsetted_today}&date_to={days_later}&last_donation=&page={counter}&radius=&term="
        response = fetch_page(page_url)
        data = response.text
        soup = BeautifulSoup(data, "lxml")

        # Stopping after the last page
        alert = soup.find(class_="alert-dismissable")
        if alert is not None:
            next_page = False

        if counter >= MAX_PAGES:
            next_page = False
            print(
                f"STOPPED AT THE {MAX_PAGES}-PAGE LIMIT without seeing the "
                "end-of-results alert. The 'alert-dismissable' class has most "
                "likely been renamed on the DRK site — check the parser against "
                "a page by hand, because the results above may be incomplete."
            )

        all_cards = soup.find_all(class_="item")
        for card in all_cards:
            # Get Date
            date = card.find(class_="datum").find(name="p").string
            normalized_date = datetime.strptime(date, '%d.%m.%Y').date()

            # Get Address
            full_address = card.find(class_="adresse")

            full_address_list = []
            for line in full_address:
                if line.string is not None:
                    full_address_list.append(line.string.strip().replace("\n", ""))
            full_address_list = [x for x in full_address_list if x][:-1]

            times = full_address_list[3:]
            full_address_list = full_address_list[:3]

            city_and_code = full_address_list[0].split()

            postal_code = [code for code in city_and_code if code.isdigit()]

            # Get Link
            link = card.find(class_="call-to-action").find(name="a").get("href")
            full_link = f"https://www.drk-blutspende.de{link}"

            manage_db.insert_termin(postal_code, full_address_list, times, normalized_date, full_link)
            manage_db.insert_termin_postcodes(postal_code)
        if counter % 5 == 0:
            print(f"{counter} pages are checked...")

    print(f"Total number of checked pages: {counter}")


manage_db.create_tables()
print("Running first parser...")
parse_pages(DELTA, OFFSET)
manage_db.delete_outdated_data()

