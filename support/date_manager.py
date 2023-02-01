from datetime import datetime
from datetime import date
from datetime import timedelta


class DateManager:

    def get_time_range(self, delta, start_date_offset):
        today = datetime.today()
        offsetted_today = today + timedelta(days=start_date_offset)
        week_later = today + timedelta(days=delta)
        offsetted_today = offsetted_today.strftime("%Y-%m-%d")
        week_later = week_later.strftime("%Y-%m-%d")

        return offsetted_today, week_later

    def get_today(self):
        today = date.today()
        return today

    def get_now(self):
        now = datetime.now()
        formatted_now = now.strftime("%Y-%m-%d %H:%M:%S")
        return formatted_now, now

    def get_min_from_now(self, mins):
        now = datetime.now()
        offsetted_now = now + timedelta(minutes=mins)
        offsetted_now = offsetted_now.strftime("%Y-%m-%d %H:%M:%S")
        return offsetted_now

    def get_days_from_today(self, days):
        today = datetime.today()
        days_from_now = today + timedelta(days=days)
        days_from_now = days_from_now.strftime("%Y-%m-%d")
        return days_from_now

    def format_date(self, my_date):
        my_date = my_date.strftime("%d.%m.%Y")
        return my_date

    def get_date_delta(self, termin_date):
        today = self.get_today()
        difference = termin_date - today
        return difference.days
