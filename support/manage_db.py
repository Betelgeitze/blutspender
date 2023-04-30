from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, Date, TIMESTAMP, UniqueConstraint, \
    and_, text, BIGINT
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import relationship, sessionmaker
import os
from support.postcode_ranges import PostcodeRanges
from support.date_manager import DateManager


class ManageDB:

    def __init__(self, country_code):
        self.Base, self.engine, self.Termine, self.Times, self.Postcodes, \
        self.Users, self.UserPostcodes, self.Feedback, self.ReminderDays = self.create_db_structure()

        self.postcode_ranges = PostcodeRanges(country_code=country_code)
        self.date_manager = DateManager()

# Managing tables
    def create_db_structure(self):
        credentials = f'postgresql://{os.environ["POSTGRES_USER"]}:{os.environ["POSTGRES_PASSWORD"]}@{os.environ["HOSTNAME"]}:{os.environ["PORT_ID"]}/{os.environ["POSTGRES_DB"]}'
        engine = create_engine(credentials)

        Base = declarative_base()

        class Termine(Base):
            __tablename__ = "termine"
            id = Column(Integer, primary_key=True)
            postcode = Column(String(32), nullable=False)
            city = Column(String(255), nullable=False)
            building = Column(String(255), nullable=False)
            street = Column(String(255), nullable=False)
            date = Column(Date, nullable=False)
            link = Column(String(1000), nullable=False)

            children = relationship("Times", cascade="all,delete", back_populates="parent")

            __table_args__ = (UniqueConstraint("link", "date", name="uq_link_and_date"),)

        class Times(Base):
            __tablename__ = "times"
            id = Column(Integer, primary_key=True)
            termin_id = Column(Integer, ForeignKey("termine.id", ondelete="CASCADE"))
            time = Column(String(255), nullable=False)

            parent = relationship("Termine", back_populates="children")

            __table_args__ = (UniqueConstraint("termin_id", "time", name="uq_termin_id_and_time"),)

        class Postcodes(Base):
            __tablename__ = "postcodes"
            id = Column(Integer, primary_key=True)
            postcode = Column(String(32), nullable=False)
            latitude = Column(Float, nullable=False)
            longitude = Column(Float, nullable=False)

            __table_args__ = (UniqueConstraint("postcode", name="uq_postcode"),)

        class Users(Base):
            __tablename__ = "users"
            id = Column(Integer, primary_key=True)
            account_id = Column(BIGINT, nullable=False)
            chat_id = Column(BIGINT, nullable=False)
            selected_language = Column(String(32), nullable=False)
            response = Column(String(32))
            last_donation = Column(Date)
            donations = Column(Integer)
            start_reminding = Column(Date, nullable=False)
            distance = Column(Float, nullable=False)

            postcodes_children = relationship("UserPostcodes", cascade="all,delete", back_populates="parent")
            feedback_children = relationship("Feedback", cascade="all,delete", back_populates="parent")
            reminderdays_children = relationship("ReminderDays", cascade="all,delete", back_populates="parent")

            __table_args__ = (UniqueConstraint("account_id", name="uq_account_id"),)

        class UserPostcodes(Base):
            __tablename__ = "userpostcodes"
            id = Column(Integer, primary_key=True)
            user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
            postcode = Column(String(32), nullable=False)
            date_time = Column(TIMESTAMP, nullable=False)

            parent = relationship("Users", back_populates="postcodes_children")

            __table_args__ = (UniqueConstraint("user_id", "postcode", name="uq_user_id_and_postcode"),)

        class Feedback(Base):
            __tablename__ = "feedback"
            id = Column(Integer, primary_key=True)
            user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
            text = Column(String())

            parent = relationship("Users", back_populates="feedback_children")

        class ReminderDays(Base):
            __tablename__ = "reminderdays"
            id = Column(Integer, primary_key=True)
            user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
            reminder_day = Column(Integer)

            parent = relationship("Users", back_populates="reminderdays_children")
            __table_args__ = (UniqueConstraint("user_id", "reminder_day", name="uq_user_id_and_reminder_day"),)

        return Base, engine, Termine, Times, Postcodes, Users, UserPostcodes, Feedback, ReminderDays

    def create_tables(self):
        self.Base.metadata.create_all(self.engine)

    def delete_tables(self, tables):
        for table in tables:
            sql = text(f"DROP TABLE IF EXISTS {table} CASCADE;")
            with self.engine.connect() as connection:
                with connection.begin():
                    connection.execute(sql)

# Support functions
    def write_into_db(self, data, session):
        # Catching dublicates
        try:
            session.add(data)
            session.commit()
        except IntegrityError:
            session.rollback()
        finally:
            session.close()

    def session_maker(self):
        Session = sessionmaker(self.engine)
        session = Session()
        return session

    def get_user(self, account_id):
        session = self.session_maker()
        user = session.query(self.Users).filter(self.Users.account_id == account_id).first()
        return user, session

# Reading from Tables
    def get_user_data(self, account_id):
        user, session = self.get_user(account_id)
        session.close()
        return user

    def get_reminder_days(self, account_id):
        user, session = self.get_user(account_id)
        filtered_table = session.query(self.ReminderDays).filter(self.ReminderDays.user_id == user.id).all()
        session.close()
        days = [row.reminder_day for row in filtered_table]
        return days

    def get_user_postcodes(self, account_id):
        user, session = self.get_user(account_id)
        postcode_data = session.query(self.UserPostcodes).filter(self.UserPostcodes.user_id == user.id).all()
        session.close()
        if postcode_data:
            return [row.postcode for row in postcode_data]
        else:
            return []

    def get_postcodes_nearby(self, distance, postcode, min_lat, max_lat, min_lon, max_lon, inform_days):
        available_termine = []
        postcodes_nearby = []

        session = self.session_maker()

        postcodes_data = session.query(self.Postcodes).filter(and_(
            self.Postcodes.latitude < max_lat,
            self.Postcodes.latitude > min_lat,
            self.Postcodes.longitude < max_lon,
            self.Postcodes.longitude > min_lon)).all()

        termin_postcodes = [item.postcode for item in postcodes_data]

        for termin_postcode in termin_postcodes:
            termin_distance = self.postcode_ranges.check_distance(postcode, termin_postcode)
            if termin_distance <= distance:
                postcodes_nearby.append(termin_postcode)

        available_termin_data = session.query(self.Termine).filter(
            self.Termine.postcode.in_(postcodes_nearby)).all()

        for row in available_termin_data:
            times_data = session.query(self.Times).filter(self.Times.termin_id == row.id).all()
            date_delta = self.date_manager.get_date_delta(row.date)
            formatted_date = self.date_manager.format_date(row.date)

            if inform_days is None or date_delta in inform_days:
                times = [item.time for item in times_data]
                available_termin = row.__dict__
                useless_keys = ["_sa_instance_state", "id", "postcode"]
                for useless_key in useless_keys:
                    available_termin.pop(useless_key, None)
                available_termin["date"] = formatted_date
                available_termin["times"] = times
                available_termine.append(available_termin)
        session.close()
        return available_termine

    def get_available_termine(self, approximate_max_distance, max_distance, inform_days):
        found_termine_data = []
        session = self.session_maker()
        today = self.date_manager.get_today()

        users = session.query(self.Users).filter(self.Users.start_reminding <= today).all()
        for user in users:
            available_termin_data = []
            unique_termine = []
            postcode_data = session.query(self.UserPostcodes).filter(self.UserPostcodes.user_id == user.id).all()
            user_postcodes = [item.postcode for item in postcode_data]
            for postcode in user_postcodes:
                lat, lon = self.postcode_ranges.get_lat_and_lon(postcode=postcode)
                min_lat, max_lat, min_lon, max_lon = self.postcode_ranges.calculate_ranges(approximate_max_distance,
                                                                                           lat, lon)
                available_termine = self.get_postcodes_nearby(max_distance, postcode, min_lat, max_lat, min_lon,
                                                              max_lon, inform_days)
                if len(available_termine) > 0:
                    available_termin_data.append(available_termine)
            if not len(available_termin_data) == 0:
                # Remove dublicates
                for elem in available_termin_data:
                    if elem not in unique_termine:
                        unique_termine.append(elem)
                found_termine = {
                    "account_id": user.account_id,
                    "chat_id": user.chat_id,
                    "available_termine": unique_termine
                }
                found_termine_data.append(found_termine)
        session.close()
        return found_termine_data

    def check_if_remind(self, account_id):
        user, session = self.get_user(account_id)
        today = self.date_manager.get_today()
        formatted_reminder_start = self.date_manager.format_date(user.start_reminding)
        session.close()
        if today < user.start_reminding:
            return False, formatted_reminder_start
        else:
            return True, formatted_reminder_start

# Inserting in Tables
    def insert_termin(self, postcode, full_address_list, times, normalized_date, full_link):
        session = self.session_maker()
        # Inserting data in termine table
        new_termin = self.Termine(
            postcode=postcode[0],
            city=full_address_list[0],
            building=full_address_list[1],
            street=full_address_list[2],
            date=normalized_date,
            link=full_link
        )
        # Inserting data in times table via termine table
        for time in times:
            new_time = self.Times(
                time=time
            )
            new_termin.children.append(new_time)

        self.write_into_db(new_termin, session)

    def insert_termin_postcodes(self, postcode):
        session = self.session_maker()
        lat, lon = self.postcode_ranges.get_lat_and_lon(postcode=postcode[0])
        # Inserting data in postcodes table
        new_postcode = self.Postcodes(
            postcode=postcode[0],
            latitude=lat,
            longitude=lon
        )
        self.write_into_db(new_postcode, session)

    def insert_users(self, user_data, default_distance, default_language):
        session = self.session_maker()
        new_user = self.Users(
            account_id=user_data["from"]["id"],
            chat_id=user_data["chat"]["id"],
            response="postcode",
            donations=0,
            selected_language=default_language,
            start_reminding=self.date_manager.get_now()[0],
            distance=default_distance
        )

        self.write_into_db(new_user, session)

    def insert_user_postcodes(self, account_id, text):
        user, session = self.get_user(account_id)

        new_user_postcode = self.UserPostcodes(
            parent=user,
            user_id=account_id,
            postcode=text,
            date_time=self.date_manager.get_now()[0]
        )

        self.write_into_db(new_user_postcode, session)

    def insert_feedback(self, account_id, text):
        user, session = self.get_user(account_id)

        new_feedback = self.Feedback(
            parent=user,
            text=text

        )
        self.write_into_db(new_feedback, session)

    def insert_reminder_days(self, account_id, days):
        user, session = self.get_user(account_id)
        session.query(self.ReminderDays).filter(self.ReminderDays.user_id == user.id).delete()
        session.commit()
        session.close()
        for day in days:
            user, session = self.get_user(account_id)
            new_day = self.ReminderDays(
                parent=user,
                reminder_day=day
            )
            self.write_into_db(new_day, session)

# Updating tables
    def update_user(self, account_id, column, value):
        user, session = self.get_user(account_id)
        if column == "start_reminding":
            value = self.date_manager.get_days_from_today(days=value)
        setattr(user, column, value)
        self.write_into_db(user, session)

    def addup_donations(self, account_id):
        today = self.date_manager.get_today()
        user, session = self.get_user(account_id)
        # User can tell that he donated only once a day
        if today != user.last_donation:
            user.donations += 1
            user.last_donation = today
            self.write_into_db(user, session)
        else:
            session.close()

# Deleting from Tables
    def delete_outdated_data(self):
        session = self.session_maker()

        today = self.date_manager.get_today()

        session.query(self.Termine).filter(self.Termine.date <= today).delete()
        session.commit()
        session.close()

    def delete_user_postcode(self, account_id, command):
        user, session = self.get_user(account_id)
        postcode_row = 0
        if command.lower() == "all":
            session.query(self.UserPostcodes).filter(self.UserPostcodes.user_id == user.id).delete()
        else:
            postcode_row = session.query(self.UserPostcodes).filter(self.UserPostcodes.user_id == user.id).filter(
                self.UserPostcodes.postcode == command).first()
            session.query(self.UserPostcodes).filter(self.UserPostcodes.user_id == user.id).filter(
                self.UserPostcodes.postcode == command).delete()

        session.commit()
        session.close()
        return postcode_row

    def delete_user(self, account_id):
        user, session = self.get_user(account_id)
        session.query(self.Users).filter(self.Users.id == user.id).delete()
        session.commit()
        session.close()
