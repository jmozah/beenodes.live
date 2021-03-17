import sqlite3

conn = sqlite3.connect('beenodeslive.db')
print("Opened database successfully")


conn.execute('''CREATE TABLE IP_INFO
         (IP TEXT PRIMARY KEY,
          LAT            REAL     NOT NULL,
          LNG            REAL     NOT NULL,
          CITY           TEXT     NOT NULL,
          Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP);''')
print("Table IP_INFO created successfully")

conn.execute('''CREATE TABLE CITY_INFO (
          BATCH           TEXT     NOT NULL,
          CITY            TEXT     NOT NULL,
          LAT             REAL     NOT NULL,
          LNG             REAL     NOT NULL,
          GREEN_COUNT     INTEGER  NOT NULL,
          ORANGE_COUNT    INTEGER  NOT NULL,
          RED_COUNT       INTEGER  NOT NULL,
          Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY(BATCH, CITY));''')
conn.execute('''CREATE INDEX city_info_date on CITY_INFO(BATCH)''')
print("Table CITY_INFO created successfully")

conn.close()