#!/usr/bin/python
  
import sqlite3

conn = sqlite3.connect('beenodeslive.db')
print("Opened database successfully");

conn.execute('''CREATE TABLE IPTOCITY
         (IP TEXT PRIMARY KEY     NOT NULL,
          LAT            REAL     NOT NULL,
          LNG            REAL     NOT NULL,
          CITY           TEXT    NOT NULL);''')
print("Table IPTOCITY created successfully");

conn.execute('''CREATE TABLE OVERLAYTOIP
         (OVERLAY  TEXT  PRIMARY KEY,
          IP           TEXT    NOT NULL);''')
print("Table OVERLAYTOIP created successfully");

conn.execute('''CREATE TABLE BEENODES
         (ID INTEGER PRIMARY KEY,
          DATE            TEXT     NOT NULL,
          CITY            TEXT     NOT NULL,
          COUNT           INTEGER    NOT NULL);''')
conn.execute('''CREATE INDEX batch on BEENODES(DATE)''')
print("Table BEENODES created successfully");
conn.close()

