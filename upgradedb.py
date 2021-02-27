import sqlite3

conn = sqlite3.connect('beenodeslive.db')
print("Opened database successfully")

conn.execute('''DROP TABLE IF EXISTS OVERLAYTOIP''')
print("Dropped table  OVERLAYTOIP successfully")

conn.execute('''DROP TABLE IF EXISTS BEENODES''')
print("Dropped table  BEENODES successfully")

conn.execute('''DROP TABLE IF EXISTS COUNTERS''')
print("Dropped table  COUNTERS successfully")

conn.execute('''DROP TABLE IF EXISTS CITYBATCH''')
print("Dropped table CITYBATCH successfully")

conn.execute('''DROP TABLE IF EXISTS OVERLAYIPPORT''')
print("Dropped table OVERLAYIPPORT successfully")

conn.execute('''DROP INDEX IF EXISTS beenodes_date''')
print("Dropped index  beenodes_date successfully")

conn.execute('''DROP INDEX IF EXISTS citybatch_date''')
print("Dropped index  citybatch_date successfully")

conn.execute('''CREATE TABLE IP_INFO
         (IP TEXT PRIMARY KEY,
          LAT            REAL     NOT NULL,
          LNG            REAL     NOT NULL,
          CITY           TEXT     NOT NULL,
          Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP);''')
print("Table IP_INFO created successfully")

print('moving data from IPTOCITY to IP_INFO')
cursor = conn.execute('''SELECT IP, CITY, LAT, LNG FROM  IPTOCITY''')
ip_info = dict()
for row in cursor:
    ip = row[0]
    city = row[1]
    lat = row[2]
    lng = row[3]
    ip_info[ip] = (city, lat, lng)
count = 0
for ip in ip_info:
    (city, lat, lng) = ip_info[ip]
    conn.execute('insert into IP_INFO (IP, CITY, LAT, LNG) values(?, ?, ?, ?)', (ip, city, lat, lng))
    count += 1
conn.commit()
print('moved {} rows from IPTOCITY to IP_INFO'.format(str(count)))

conn.execute('''DROP TABLE IF EXISTS IPTOCITY''')
print("Dropped table IPTOCITY successfully")

conn.execute('''CREATE TABLE PEER_INFO (
          BATCH        TEXT    NOT NULL,
          OVERLAY      TEXT    NOT NULL,
          UNDERLAY     TEXT    NOT NULL,
          PEERS_COUNT  INTEGER NOT NULL,
          Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY(BATCH, OVERLAY));''')
print("Table PEER_INFO created successfully")


conn.execute('''CREATE TABLE NEIGHBOUR_INFO (
          BATCH                TEXT    NOT NULL,
          BASE_OVERLAY         TEXT    NOT NULL,
          NEIGHBOUR_OVERLAY    TEXT    NOT NULL,
          NEIGHBOUR_IP4or6     TEXT    NOT NULL,
          NEIGHBOUR_IP         TEXT    NOT NULL,
          NEIGHBOUR_PROTOCOL   TEXT    NOT NULL,
          NEIGHBOUR_PORT       TEXT    NOT NULL,
          NEIGHBOUR_UNDERLAY   TEXT    NOT NULL,
          Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY(BATCH, BASE_OVERLAY, NEIGHBOUR_OVERLAY));''')
print("Table NEIGHBOUR_INFO created successfully")


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