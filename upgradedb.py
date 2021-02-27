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

conn.execute('''DROP TABLE IF EXISTS PEER_INFO''')
print("Dropped table PEER_INFO successfully")

conn.execute('''DROP TABLE IF EXISTS NEIGHBOUR_INFO''')
print("Dropped table NEIGHBOUR_INFO successfully")

conn.execute('''DROP TABLE IF EXISTS IPTOCITY''')
print("Dropped table IPTOCITY successfully")


conn.execute('''DROP INDEX IF EXISTS beenodes_date''')
print("Dropped index  beenodes_date successfully")

conn.execute('''DROP INDEX IF EXISTS citybatch_date''')
print("Dropped index  citybatch_date successfully")

conn.execute('''DROP INDEX IF EXISTS neighbour_info_neighbour_overlay_date''')
print("Dropped index  neighbour_info_neighbour_overlay_date successfully")

conn.close()