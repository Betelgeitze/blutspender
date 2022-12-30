from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, Date, TIMESTAMP, UniqueConstraint, \
    and_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import relationship, sessionmaker
import os
import json
from postcode_ranges import PostcodeRanges
from date_manager import DateManager


class ManageDB:

    def __init__(self):
        self.Base, self.engine, self.Termine, self.Times, self.Postcodes, self.Users, self.UserPostcodes, self.Feedback = self.create_db_structure()

        self.postcode_ranges = PostcodeRanges()
        self.date_manager = DateManager()

        Session = sessionmaker(self.engine)
        self.session = Session()

    def create_db_structure(self):
        engine = create_engine(f'postgresql://'
                               f'{os.environ["USERNAME"]}:'
                               f'{os.environ["PWD"]}@{os.environ["HOSTNAME"]}:'
                               f'{os.environ["PORT_ID"]}/{os.environ["DATABASE"]}')

        Base = declarative_base()

        class Termine(Base):
            __tablename__ = "termine"
            id = Column(Integer, primary_key=True)
            postal_code = Column(String(32), nullable=False)
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
            postal_code = Column(String(32), nullable=False)
            latitude = Column(Float, nullable=False)
            longitude = Column(Float, nullable=False)

            __table_args__ = (UniqueConstraint("postal_code", name="uq_postal_code"),)

        class Users(Base):
            __tablename__ = "users"
            id = Column(Integer, primary_key=True)
            account_id = Column(Integer, nullable=False)
            chat_id = Column(Integer, nullable=False)
            first_name = Column(String(255))
            last_name = Column(String(255))
            language_code = Column(String(32))
            selected_language = Column(String(32))  # TODO: Add:  nullable=False
            opened_to_add_postcode = Column(TIMESTAMP)
            opened_to_add_feedback = Column(TIMESTAMP)
            start_reminding = Column(Date)

            postcodes_children = relationship("UserPostcodes", cascade="all,delete", back_populates="parent")
            feedback_children = relationship("Feedback", cascade="all,delete", back_populates="parent")

            __table_args__ = (UniqueConstraint("account_id", name="uq_account_id"),)

        class UserPostcodes(Base):
            __tablename__ = "userpostcodes"
            id = Column(Integer, primary_key=True)
            user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
            postal_code = Column(String(32), nullable=False)
            date_time = Column(TIMESTAMP, nullable=False)

            parent = relationship("Users", back_populates="postcodes_children")

            __table_args__ = (UniqueConstraint("user_id", "postal_code", name="uq_user_id_and_postal_code"),)

        class Feedback(Base):
            __tablename__ = "feedback"
            id = Column(Integer, primary_key=True)
            user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
            text = Column(String())

            parent = relationship("Users", back_populates="feedback_children")

        return Base, engine, Termine, Times, Postcodes, Users, UserPostcodes, Feedback

    def create_dbs(self):
        self.Base.metadata.create_all(self.engine)

    def write_into_db(self, data):
        # Catching dublicates
        try:
            # Add termin
            self.session.add(data)
            self.session.commit()
        except IntegrityError as error_message:
            self.session.rollback()
        except KeyError as error_message:
            print(f"Error Message: {error_message}")
        finally:
            self.session.close()

    def insert_termin_data_in_db(self, postal_code, full_address_list, times, normalized_date, full_link):
        # Inserting data in termine table
        new_termin = self.Termine(
            postal_code=postal_code[0],
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

    def insert_postal_codes_in_db(self, postal_code):
        lat, lon = self.postcode_ranges.get_lat_and_lon(postal_code[0])
        # Inserting data in postcodes table
        new_postal_code = self.Postcodes(
            postal_code=postal_code[0],
            latitude=lat,
            longitude=lon
        )
        self.write_into_db(new_postal_code)

    def insert_users_in_db(self, user_data):
        new_user = self.Users(
            account_id=user_data["from"]["id"],
            chat_id=user_data["chat"]["id"],
            first_name=user_data["from"]["first_name"],
            last_name=user_data["from"]["last_name"],
            language_code=user_data["from"]["language_code"],
            selected_language="de"
        )

        self.write_into_db(new_user)

    def insert_user_postal_codes_in_db(self, user_data):
        user = self.session.query(self.Users).filter_by(account_id=user_data["from"]["id"]).first()

        new_user_postal_code = self.UserPostcodes(
            parent=user,
            user_id=user_data["from"]["id"],
            postal_code=user_data["text"],
            date_time=self.date_manager.get_now()[0]
        )

        self.write_into_db(new_user_postal_code)

    def insert_feedback(self, user_data):
        user = self.session.query(self.Users).filter_by(account_id=user_data["from"]["id"]).first()

        new_feedback = self.Feedback(
            parent=user,
            # TODO: Make all of these congruent. Not account_id/message.send_from.if/etc
            user_id=user_data["from"]["id"],
            text=user_data["text"]

        )

        self.write_into_db(new_feedback)

    def delete_outdated_data_in_db(self):
        today = self.date_manager.get_today()

        self.session.query(self.Termine).filter(self.Termine.date < today).delete()
        self.session.commit()
        self.session.close()

    def delete_tables_in_db(self, tables):
        for table in tables:
            self.engine.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")

    def get_postalcodes_nearby(self, max_distance, postal_code, min_lat, max_lat, min_lon, max_lon):
        available_termine = []
        postal_codes_nearby = []

        postcodes_data = self.session.query(self.Postcodes).filter(and_(
            self.Postcodes.latitude < max_lat,
            self.Postcodes.latitude > min_lat,
            self.Postcodes.longitude < max_lon,
            self.Postcodes.longitude > min_lon)).all()

        termin_postal_codes = [item.postal_code for item in postcodes_data]

        for postcode in termin_postal_codes:
            distance = self.postcode_ranges.check_distance(postal_code, postcode)
            if distance <= max_distance:
                postal_codes_nearby.append(postcode)

        available_termin_data = self.session.query(self.Termine).filter(
            self.Termine.postal_code.in_(postal_codes_nearby)).all()

        for row in available_termin_data:
            times_data = self.session.query(self.Times).filter(self.Times.termin_id == row.id).all()
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

    def check_available_termine(self, APPROXIMATE_MAX_DISTANCE, MAX_DISTANCE):
        found_termine = []
        available_termin_data = []
        users = self.session.query(self.Users).all()
        for user in users:
            postcode_data = self.session.query(self.UserPostcodes).filter(self.UserPostcodes.user_id == user.id).all()
            user_postcodes = [item.postal_code for item in postcode_data]
            for postal_code in user_postcodes:
                lat, lon = self.postcode_ranges.get_lat_and_lon(postal_code=postal_code)
                min_lat, max_lat, min_lon, max_lon = self.postcode_ranges.calculate_ranges(APPROXIMATE_MAX_DISTANCE,
                                                                                           lat, lon)
                available_termine = self.get_postalcodes_nearby(MAX_DISTANCE, postal_code, min_lat, max_lat, min_lon,
                                                                max_lon)
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

    def check_if_user_postal_code_exists(self, account_id):
        user = self.session.query(self.Users).filter(self.Users.account_id == account_id).first()
        postcode_data = self.session.query(self.UserPostcodes).filter(self.UserPostcodes.user_id == user.id).all()
        if postcode_data:
            user_postal_codes = [row.postal_code for row in postcode_data]
            return True, user_postal_codes
        else:
            return False, []

    def update_user_opened_to_add_postcode(self, account_id, open, **kwargs):
        user = self.session.query(self.Users).filter(self.Users.account_id == account_id).first()
        if open:
            user.opened_to_add_postcode = self.date_manager.get_min_from_now(kwargs.get("minutes"))
        else:
            user.opened_to_add_postcode = self.date_manager.get_now()[0]

        self.write_into_db(user)

    def check_if_user_add_to_postode_is_opened(self, account_id):
        user = self.session.query(self.Users).filter(self.Users.account_id == account_id).first()
        now = self.date_manager.get_now()[1]
        if user.opened_to_add_postcode is not None and user.opened_to_add_postcode > now:
            return True
        else:
            return False

    def delete_user_postal_code(self, account_id, command):
        user = self.session.query(self.Users).filter(self.Users.account_id == account_id).first()
        postcode_row = 0
        if command.lower() == "all":
            self.session.query(self.UserPostcodes).filter(self.UserPostcodes.user_id == user.id).delete()
        else:
            postcode_row = self.session.query(self.UserPostcodes).filter(self.UserPostcodes.user_id == user.id).filter(
                self.UserPostcodes.postal_code == command).first()
            self.session.query(self.UserPostcodes).filter(self.UserPostcodes.user_id == user.id).filter(
                self.UserPostcodes.postal_code == command).delete()

        self.session.commit()
        self.session.close()
        return postcode_row

    def select_language(self, account_id, language):
        user = self.session.query(self.Users).filter(self.Users.account_id == account_id).first()
        user.selected_language = language
        self.write_into_db(user)

    def check_language(self, account_id):
        user = self.session.query(self.Users).filter(self.Users.account_id == account_id).first()
        return user.selected_language

    def update_opened_feedback(self, account_id, open, **kwargs):  # TODO: Refactor all Database updates
        user = self.session.query(self.Users).filter(self.Users.account_id == account_id).first()
        if open:
            user.opened_to_add_feedback = self.date_manager.get_min_from_now(kwargs.get("minutes"))
        else:
            user.opened_to_add_feedback = self.date_manager.get_now()[0]
        self.write_into_db(user)

    def check_if_feedback_opened(self, account_id):
        user = self.session.query(self.Users).filter(self.Users.account_id == account_id).first()
        now = self.date_manager.get_now()[1]
        if user.opened_to_add_feedback is not None and user.opened_to_add_feedback > now:
            return True
        else:
            return False
