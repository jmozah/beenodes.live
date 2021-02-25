import sqlite3

conn = sqlite3.connect('beenodeslive.db')
print("Opened database successfully")

conn.execute('''DROP TABLE IF EXISTS BEENODES''')
print("Dropped table  BEENODES successfully")

conn.execute('''DROP TABLE IF EXISTS COUNTERS''')
print("Dropped table  COUNTERS successfully")

conn.execute('''DROP INDEX IF EXISTS beenodes_date''')
print("Dropped index  beenodes_date successfully")


conn.execute('''DROP TABLE IF EXISTS CITYBATCH''')
print("Dropped table CITYBATCH successfully")


conn.execute('''CREATE TABLE CITYBATCH
         (ID INTEGER PRIMARY KEY,
          DATE            TEXT     NOT NULL,
          LAT             REAL     NOT NULL,
          LNG             REAL     NOT NULL,
          CITY            TEXT     NOT NULL,
          C_COUNT         INTEGER  NOT NULL,
          D_COUNT         INTEGER  NOT NULL,
          Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP);''')
conn.execute('''CREATE INDEX citybatch_date on CITYBATCH(DATE)''')
print("Table CITYBATCH created successfully")

conn.execute('''CREATE TABLE COUNTERS
         (DATE                  TEXT PRIMARY KEY,         
          TOTAL_PEERS           INTEGER     NOT NULL,
          CONNECTED_PEERS       INTEGER     NOT NULL,
          DISCONNECTED_PEERS    INTEGER     NOT NULL,
          NEW_PEERS             INTEGER     NOT NULL,
          NEW_IPS               INTEGER     NOT NULL,
          NEW_CITIS             INTEGER     NOT NULL,
          TOTAL_ROWS_IN_BATCH   INTEGER     NOT NULL,          
          ERR_SELECTING_IP      INTEGER     NOT NULL,
          ERR_INSERTING_IP      INTEGER     NOT NULL,
          ERR_NOIP              INTEGER     NOT NULL,
          ERR_SELECTING_CITY    INTEGER     NOT NULL,
          ERR_INSERTING_CITY    INTEGER     NOT NULL,
          ERR_NOCITY            INTEGER     NOT NULL,
          ERR_INSERTING_CITYBATCH  INTEGER     NOT NULL,
          Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP);''')
print("Table COUNTERS created successfully")
conn.close()