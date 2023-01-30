from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, Date, TIMESTAMP, UniqueConstraint, \
    and_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import IntegrityError, IllegalStateChangeError
from sqlalchemy.orm import relationship, sessionmaker
import os
from support.postcode_ranges import PostcodeRanges
from support.date_manager import DateManager


class ManageDB:

    def __init__(self, country_code):
        self.Base, self.engine, self.Termine, self.Times, self.Postcodes, self.Users, self.UserPostcodes, self.Feedback = self.create_db_structure()

        self.postcode_ranges = PostcodeRanges(country_code=country_code)
        self.date_manager = DateManager()

        Session = sessionmaker(self.engine)
        self.session = Session()

# Managing tables

    def create_db_structure(self):
        engine = create_engine(f'postgresql://'
                               f'{os.environ["POSTGRES_USER"]}:'
                               f'{os.environ["POSTGRES_PASSWORD"]}@{os.environ["HOSTNAME"]}:'
                               f'{os.environ["PORT_ID"]}/{os.environ["POSTGRES_DB"]}')

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
            account_id = Column(Integer, nullable=False)
            chat_id = Column(Integer, nullable=False)
            language_code = Column(String(32))
            selected_language = Column(String(32), nullable=False)
            postcode_timer = Column(TIMESTAMP)
            feedback_timer = Column(TIMESTAMP)
            donations = Column(Integer)
            start_reminding = Column(Date, nullable=False)

            postcodes_children = relationship("UserPostcodes", cascade="all,delete", back_populates="parent")
            feedback_children = relationship("Feedback", cascade="all,delete", back_populates="parent")

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
            user_id = Column(Integer, ForeignKey("users.id"))
            text = Column(String())

            parent = relationship("Users", back_populates="feedback_children")

        return Base, engine, Termine, Times, Postcodes, Users, UserPostcodes, Feedback

    def create_tables(self):
        self.Base.metadata.create_all(self.engine)

    def delete_tables(self, tables):
        for table in tables:
            self.engine.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")

# Support functions

    def write_into_db(self, data):
        # Catching dublicates
        Session = sessionmaker(self.engine)
        with Session.begin() as session:
            session.add(data)
        # try:
        #     # Add termin
        #     # self.session.flush()
        #     self.session.add(data)
        #     self.session.commit()
        #     # self.session.close()
        # except IntegrityError:
        #     self.session.rollback()
        #     # self.session.close()
        # except IllegalStateChangeError:
        #     #We need this exception for deploying in AWS.
        #     #As it takes time to deploy and turn on the database. If you try to add smth in the meantime, it will fail
        #     pass


    def get_user(self, account_id):
        return self.session.query(self.Users).filter(self.Users.account_id == account_id).first()

# Inserting in Database

    def insert_termin(self, postcode, full_address_list, times, normalized_date, full_link):
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

        self.write_into_db(new_termin)

    def insert_termin_postcodes(self, postcode):
        lat, lon = self.postcode_ranges.get_lat_and_lon(postcode=postcode[0])
        # Inserting data in postcodes table
        new_postcode = self.Postcodes(
            postcode=postcode[0],
            latitude=lat,
            longitude=lon
        )
        self.write_into_db(new_postcode)

    def insert_users(self, user_data):
        new_user = self.Users(
            account_id=user_data["from"]["id"],
            chat_id=user_data["chat"]["id"],
            language_code=user_data["from"]["language_code"],
            postcode_timer=self.date_manager.get_now()[0],
            feedback_timer=self.date_manager.get_now()[0],
            donations=0,
            selected_language="de",
            start_reminding=self.date_manager.get_now()[0]
        )

        self.write_into_db(new_user)

    def insert_user_postcodes(self, account_id, text):
        user = self.get_user(account_id)

        new_user_postcode = self.UserPostcodes(
            parent=user,
            user_id=account_id,
            postcode=text,
            date_time=self.date_manager.get_now()[0]
        )

        self.write_into_db(new_user_postcode)

    def insert_feedback(self, account_id, text):
        user = self.get_user(account_id)

        new_feedback = self.Feedback(
            parent=user,
            user_id=account_id,
            text=text

        )

        self.write_into_db(new_feedback)

# Deleting from Database

    def delete_outdated_data(self):
        today = self.date_manager.get_today()

        self.session.query(self.Termine).filter(self.Termine.date < today).delete()
        self.session.commit()
        self.session.close()


# Scheduling: Checking available Termine

    def get_postcodes_nearby(self, max_distance, postcode, min_lat, max_lat, min_lon, max_lon, inform_days):
        available_termine = []
        postcodes_nearby = []

        postcodes_data = self.session.query(self.Postcodes).filter(and_(
            self.Postcodes.latitude < max_lat,
            self.Postcodes.latitude > min_lat,
            self.Postcodes.longitude < max_lon,
            self.Postcodes.longitude > min_lon)).all()

        termin_postcodes = [item.postcode for item in postcodes_data]

        for termin_postcode in termin_postcodes:
            distance = self.postcode_ranges.check_distance(postcode, termin_postcode)
            if distance <= max_distance:
                postcodes_nearby.append(termin_postcode)

        available_termin_data = self.session.query(self.Termine).filter(
            self.Termine.postcode.in_(postcodes_nearby)).all()


        for row in available_termin_data:
            times_data = self.session.query(self.Times).filter(self.Times.termin_id == row.id).all()
            date_delta = self.date_manager.get_date_delta(row.date)

            if inform_days is None or date_delta in inform_days:
                times = [item.time for item in times_data]

                available_termin = {
                    "Stadt": row.city,
                    "Strasse": row.street,
                    "Ort": row.building,
                    "Datum": str(row.date),
                    "Zeiten": times,
                    "Registrierungslink": row.link
                }

                available_termine.append(available_termin)

        return available_termine

    def check_available_termine(self, approximate_max_distance, max_distance, inform_days):
        found_termine = []
        available_termin_data = []
        users = self.session.query(self.Users).all()
        for user in users:
            postcode_data = self.session.query(self.UserPostcodes).filter(self.UserPostcodes.user_id == user.id).all()
            user_postcodes = [item.postcode for item in postcode_data]
            for postcode in user_postcodes:
                lat, lon = self.postcode_ranges.get_lat_and_lon(postcode=postcode)
                min_lat, max_lat, min_lon, max_lon = self.postcode_ranges.calculate_ranges(approximate_max_distance,
                                                                                           lat, lon)
                available_termine = self.get_postcodes_nearby(max_distance, postcode, min_lat, max_lat, min_lon,
                                                              max_lon, inform_days)
                if len(available_termine) > 0:
                    available_termin_data.append(available_termine)

            for row in available_termin_data:
                found_termin = {
                    "user": user.account_id,
                    "chat_id": user.chat_id,
                    "language_code": user.language_code,
                    "available_termine": row[0]
                }
                found_termine.append(found_termin)
        return found_termine

# Checking Postcodes

    def get_user_postcodes(self, account_id):
        user = self.get_user(account_id)
        postcode_data = self.session.query(self.UserPostcodes).filter(self.UserPostcodes.user_id == user.id).all()
        if postcode_data:
            user_postcodes = [row.postcode for row in postcode_data]
            return True, user_postcodes
        else:
            return False, []

# Writing extra data: Working with Timers

    def update_timers(self, account_id, open, timer, **kwargs):
        user = self.get_user(account_id)
        if open:
            setattr(user, timer, self.date_manager.get_min_from_now(kwargs.get("minutes")))
        else:
            setattr(user, timer, self.date_manager.get_now()[0])
        self.write_into_db(user)

    def check_timers(self, account_id, timer):
        user = self.get_user(account_id)
        now = self.date_manager.get_now()[1]
        if getattr(user, timer) > now:
            return True
        else:
            return False

# User delete postcodes

    def delete_user_postcode(self, account_id, command):
        user = self.get_user(account_id)
        postcode_row = 0
        if command.lower() == "all":
            self.session.query(self.UserPostcodes).filter(self.UserPostcodes.user_id == user.id).delete()
        else:
            postcode_row = self.session.query(self.UserPostcodes).filter(self.UserPostcodes.user_id == user.id).filter(
                self.UserPostcodes.postcode == command).first()
            self.session.query(self.UserPostcodes).filter(self.UserPostcodes.user_id == user.id).filter(
                self.UserPostcodes.postcode == command).delete()

        self.session.commit()
        self.session.close()
        return postcode_row

# Languages

    def update_language(self, account_id, language):
        user = self.get_user(account_id)
        user.selected_language = language
        self.write_into_db(user)

    def get_language(self, account_id):
        user = self.get_user(account_id)
        return user.selected_language

# Reminder Stops

    def addup_donations(self, account_id):
        user = self.get_user(account_id)
        user.donations += 1
        self.write_into_db(user)

    def remind_in(self, account_id, days):
        user = self.get_user(account_id)
        user.start_reminding = self.date_manager.get_days_from_today(days=days)
        self.write_into_db(user)

    def want_remind(self, account_id):
        user = self.get_user(account_id)
        today = self.date_manager.get_today()
        formatted_reminder_start = self.date_manager.format_date(user.start_reminding)
        if today < user.start_reminding:
            return False, formatted_reminder_start
        else:
            return True, formatted_reminder_start



