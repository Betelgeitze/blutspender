def establish_connection():
    pass
# conn = None
# cur = None
# try:
#     conn = psycopg2.connect(
#         host=os.environ["HOSTNAME"],
#         dbname=os.environ["DATABASE"],
#         user=os.environ["USERNAME"],
#         password=os.environ["PWD"],
#         port=os.environ["PORT_ID"]
#     )
#     cur = conn.cursor()
#
#     create_termine_script = ''' CREATE TABLE IF NOT EXISTS termine (
#                             id  SERIAL PRIMARY KEY,
#                             postal_code int NOT NULL,
#                             city    varchar(255) NOT NULL,
#                             building    varchar(255) NOT NULL,
#                             street  varchar(255) NOT NULL,
#                             date    varchar(255) NOT NULL,
#                             link    varchar(255) NOT NULL
#                             )
#                             '''
#     cur.execute(create_termine_script)
#
#     create_times_script = ''' CREATE TABLE IF NOT EXISTS times (
#                                     id SERIAL PRIMARY KEY,
#                                     termin_id INTEGER REFERENCES termine(id),
#                                     time varchar(255) NOT NULL
#                                     )
#                                     '''
#
#     cur.execute(create_times_script)
#     conn.commit()
#
# except Exception as error:
#     print(error)
# finally:
#     return conn, cur

    def close_connection(self, conn, cur):
        if cur is not None:
            cur.close()
        if conn is not None:
            conn.close()

def insert_data_in_db():
    pass

### Insert the data in the DB
        # insert_script = '''INSERT INTO termine (
        #                                         postal_code,
        #                                         city,
        #                                         building,
        #                                         street,
        #                                         date,
        #                                         link
        #                                         ) VALUES (%s, %s, %s, %s, %s, %s)
        #                                         '''
        # # Bring arguments in the right format
        # merged_data = [postal_code, full_address_list, [date], [full_link]]
        # merged_data = [item for sublist in merged_data for item in sublist]
        #
        # cur.execute(insert_script, merged_data)
        #
        # ### Delete Dublicates
        #
        # undublicate_termine_script = ''' DELETE FROM termine
        #                             WHERE id IN
        #                                 (SELECT id
        #                                 FROM
        #                                     (SELECT id,
        #                                      ROW_NUMBER() OVER( PARTITION BY link
        #                                     ORDER BY  id ) AS row_num
        #                                     FROM termine ) t
        #                                     WHERE t.row_num > 1 );
        #                             '''
        # cur.execute(undublicate_termine_script)
        #
        # ### GET TERMIN ID
        # get_id_script = f''' SELECT id FROM termine WHERE link = '{full_link}' '''
        # cur.execute(get_id_script)
        # termin_id = cur.fetchone()[0]
        #
        # ### Add times in Times table
        # for time in times:
        #     insert_time_script = f''' INSERT INTO times (
        #                                     termin_id,
        #                                     time
        #                                     ) VALUES (%s, %s)
        #                                 '''
        #     cur.execute(insert_time_script, [termin_id, time])
        #
        # ### Dedublicate Times table
        # undublicate_times_script = ''' DELETE FROM times
        #                                     WHERE id IN
        #                                         (SELECT id
        #                                         FROM
        #                                             (SELECT id,
        #                                              ROW_NUMBER() OVER( PARTITION BY (termin_id, time)
        #                                             ORDER BY  id ) AS row_num
        #                                             FROM times ) t
        #                                             WHERE t.row_num > 1 );
        #                                     '''
        # cur.execute(undublicate_times_script)
        #
        # conn.commit()


# query = f"ALTER TABLE termine ADD FOREIGN KEY (postal_code) REFERENCES postcodes(postal_code);"
# query = f"ALTER TABLE postcodes ADD PRIMARY KEY (postal_code);"
# # query = "ALTER TABLE postcodes ADD UNIQUE (postal_code);"
# conn = engine.connect()
# conn.execute(query)


    # def calculate_dist(self, lat1, lat2, lon1, lon2):
    #     lon1 = radians(lon1)
    #     lon2 = radians(lon2)
    #     lat1 = radians(lat1)
    #     lat2 = radians(lat2)
    #
    #     dlon = lon2 - lon1
    #     dlat = lat2 - lat1
    #     a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    #
    #     c = 2 * asin(sqrt(a))
    #
    #     # Radius of earth in kilometers. Use 3956 for miles
    #     r = 6371
    #
    #     # calculate the result
    #     dist = (c * r)
    #     return dist