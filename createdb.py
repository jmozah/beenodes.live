#!/usr/bin/python
  
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

