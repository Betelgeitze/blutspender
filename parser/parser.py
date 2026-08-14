from datetime import datetime
import re
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

# The date inside a card's "datum" block. Matched by shape rather than by tag:
# in August 2026 DRK moved this text out of a <p> and into a plain <div>, and
# card.find(name="p") took the whole run down with an AttributeError. The
# dd.mm.yyyy string is the part of that block that does not move.
DATE_PATTERN = re.compile(r"\b(\d{1,2}\.\d{1,2}\.\d{4})\b")


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


def parse_card(card):
    """Read one result card, or return None if it does not look like one.

    Returning None instead of raising keeps a single odd card — DRK does put
    the occasional differently-shaped entry in the list — from discarding a
    whole run's worth of appointments. parse_pages counts what it drops and
    fails the run if the drops turn out to be everything, which is what a
    markup change on their side looks like.
    """
    datum = card.find(class_="datum")
    if datum is None:
        return None
    date_match = DATE_PATTERN.search(datum.get_text(" ", strip=True))
    if date_match is None:
        return None
    normalized_date = datetime.strptime(date_match.group(1), "%d.%m.%Y").date()

    full_address = card.find(class_="adresse")
    if full_address is None:
        return None

    full_address_list = []
    for line in full_address:
        if line.string is not None:
            full_address_list.append(line.string.strip().replace("\n", ""))
    # The last line is the "Bitte Termin reservieren!" note, not an address.
    full_address_list = [x for x in full_address_list if x][:-1]

    times = full_address_list[3:]
    full_address_list = full_address_list[:3]
    if len(full_address_list) < 3:
        return None

    city_and_code = full_address_list[0].split()
    postal_code = [code for code in city_and_code if code.isdigit()]
    if not postal_code:
        return None

    call_to_action = card.find(class_="call-to-action")
    link = None if call_to_action is None else call_to_action.find(name="a")
    if link is None:
        return None
    full_link = f"https://www.drk-blutspende.de{link.get('href')}"

    return postal_code, full_address_list, times, normalized_date, full_link


def parse_pages(delta, start_date_offset):
    # Getting times
    offsetted_today, days_later = date_manager.get_time_range(delta, start_date_offset)
    print(f"Parsing appointements from {offsetted_today} - {days_later}")

    # Parsing DRK
    next_page = True
    counter = 0
    cards_seen = 0
    cards_stored = 0
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
            cards_seen += 1
            parsed = parse_card(card)
            if parsed is None:
                print(f"Skipped an unreadable card on page {counter}")
                continue
            postal_code, full_address_list, times, normalized_date, full_link = parsed

            manage_db.insert_termin(postal_code, full_address_list, times, normalized_date, full_link)
            manage_db.insert_termin_postcodes(postal_code)
            cards_stored += 1
        if counter % 5 == 0:
            print(f"{counter} pages are checked...")

    print(f"Total number of checked pages: {counter}")
    print(f"Stored {cards_stored} of {cards_seen} cards")

    # Every card unreadable means the card markup changed, not that DRK had a
    # quiet day — and the difference matters, because delete_outdated_data()
    # runs next and users would simply stop being told about appointments. Fail
    # so run-job.sh alerts ADMIN_CHAT_ID. A genuinely empty search returns no
    # cards at all and is left alone.
    if cards_seen > 0 and cards_stored == 0:
        raise RuntimeError(
            f"Found {cards_seen} cards but could not read any of them — the DRK "
            "card markup has most likely changed. Check parse_card() against a "
            "live results page."
        )


manage_db.create_tables()
print("Running first parser...")
parse_pages(DELTA, OFFSET)
manage_db.delete_outdated_data()

