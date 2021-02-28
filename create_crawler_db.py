import sqlite3

conn = sqlite3.connect('crawler.db')
print("Opened database successfully")

conn.execute('''CREATE TABLE PEER_INFO (
          OVERLAY      TEXT    NOT NULL,
          IP4or6       TEXT    NOT NULL,
          IP           TEXT    NOT NULL,
          PROTOCOL     TEXT    NOT NULL,
          PORT         TEXT    NOT NULL,
          UNDERLAY     TEXT    NOT NULL,
          PEERS_COUNT  INTEGER NOT NULL,
          Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY(OVERLAY));''')
print("Table PEER_INFO created successfully")


conn.execute('''CREATE TABLE NEIGHBOUR_INFO (
          BASE_OVERLAY         TEXT    NOT NULL,
          PROXIMITY_ORDER      INTEGER NOT NULL,
          NEIGHBOUR_OVERLAY   TEXT    NOT NULL,
          Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY(BASE_OVERLAY, NEIGHBOUR_OVERLAY));''')
print("Table NEIGHBOUR_INFO created successfully")

conn.close()

