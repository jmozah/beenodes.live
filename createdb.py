#!/usr/bin/python
  
import sqlite3

conn = sqlite3.connect('beenodeslive.db')
print("Opened database successfully");

conn.execute('''CREATE TABLE IPTOCITY
         (ID INTEGER PRIMARY KEY,
          IP             TEXT     NOT NULL,
          LAT            REAL     NOT NULL,
          LNG            REAL     NOT NULL,
          CITY           TEXT     NOT NULL,
          Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP);''')
conn.execute('''CREATE INDEX iptocity_ip on IPTOCITY(IP)''')
print("Table IPTOCITY created successfully");

conn.execute('''CREATE TABLE OVERLAYTOIP
         (OVERLAY  TEXT  PRIMARY KEY,
          IP           TEXT    NOT NULL,
          Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP);''')
print("Table OVERLAYTOIP created successfully");

conn.execute('''CREATE TABLE BEENODES
         (ID INTEGER PRIMARY KEY,
          DATE            TEXT     NOT NULL,
          IPTOCITY_ID     INTEGER     NOT NULL,
          Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP);''')
conn.execute('''CREATE INDEX beenodes_date on BEENODES(DATE)''')
print("Table BEENODES created successfully");

conn.execute('''CREATE TABLE COUNTERS
         (ID INTEGER PRIMARY KEY,         
          TOTAL_OVERLAYS        INTEGER     NOT NULL,
          NEW_OVERLAYS          INTEGER     NOT NULL,
          NEW_IPS               INTEGER     NOT NULL,
          NEW_CITIS             INTEGER     NOT NULL,
          TOTAL_NODES           INTEGER     NOT NULL,
          ERR_INSERTING_IP      INTEGER     NOT NULL,
          ERR_INSERTING_NOIP    INTEGER     NOT NULL,
          ERR_NOIP              INTEGER     NOT NULL,
          ERR_INSERTING_CITY    INTEGER     NOT NULL,
          ERR_NOCITY            INTEGER     NOT NULL,
          ERR_INSERTING_BEENODES  INTEGER     NOT NULL,
          ERR_NO_DATELOG        INTEGER     NOT NULL,
          ERR_NO_DB             INTEGER     NOT NULL,
          Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP);''')
print("Table COUNTERS created successfully");


conn.close()

