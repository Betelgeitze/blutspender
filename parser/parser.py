from datetime import datetime
import requests
from bs4 import BeautifulSoup
from time import sleep
import random
from support.manage_db import ManageDB
from support.date_manager import DateManager


class Parser:

    def __init__(self, country_code):
        self.country_code = country_code

        self.manage_db = ManageDB(country_code)
        self.date_manager = DateManager()

    def parse_pages(self, delta, start_date_offset):
        # Getting times
        offsetted_today, days_later = self.date_manager.get_time_range(delta, start_date_offset)
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
            response = requests.get(url=page_url)
            data = response.text
            soup = BeautifulSoup(data, "lxml")

            # Stopping after the last page
            alert = soup.find(class_="alert-dismissable")
            if alert is not None:
                next_page = False

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

                self.manage_db.insert_termin(postal_code, full_address_list, times, normalized_date, full_link)
                self.manage_db.insert_termin_postcodes(postal_code)
            if counter % 5 == 0:
                print(f"{counter} pages are checked...")

        print(f"Total number of checked pages: {counter}")
