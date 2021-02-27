import sqlite3

conn = sqlite3.connect('crawler.db')
print("Opened database successfully")

conn.execute('''CREATE TABLE PEER_INFO (
          OVERLAY      TEXT    NOT NULL,
          UNDERLAY     TEXT    NOT NULL,
          PEERS_COUNT  INTEGER NOT NULL,
          Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY(OVERLAY));''')
print("Table PEER_INFO created successfully")


conn.execute('''CREATE TABLE NEIGHBOUR_INFO (
          BASE_OVERLAY         TEXT    NOT NULL,
          PROXIMITY_ORDER      INTEGER NOT NULL,
          NEIGHBOUR_OVERLAY    TEXT    NOT NULL,
          NEIGHBOUR_IP4or6     TEXT    NOT NULL,
          NEIGHBOUR_IP         TEXT    NOT NULL,
          NEIGHBOUR_PROTOCOL   TEXT    NOT NULL,
          NEIGHBOUR_PORT       TEXT    NOT NULL,
          NEIGHBOUR_UNDERLAY   TEXT    NOT NULL,
          Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY(BASE_OVERLAY, NEIGHBOUR_OVERLAY));''')
print("Table NEIGHBOUR_INFO created successfully")
conn.execute('''CREATE INDEX neighbour_info_neighbour_overlay_date on NEIGHBOUR_INFO(NEIGHBOUR_OVERLAY)''')
print("Index neighbour_info_neighbour_overlay_date created successfully")

conn.close()

