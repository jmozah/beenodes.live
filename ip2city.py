import re
import json
import requests
import sqlite3

NEW_FILE = 'new_small.txt'
OLD_FILE = 'old_small.txt'


def getDetails(fileName, sqlConn, cityMap, count, newip, cachedip, oldNew):
    file1 = open(fileName, 'r')
    Lines = file1.readlines()

    for line in Lines:
        count += 1
        ip = line.rstrip("\n")
        city = ''
        cursor = sqlConn.execute("SELECT ip, lat, lng, city from IPTOCITY where ip = ?", (ip,))
        for row in cursor:
            lat = row[1]
            lng = row[2]
            city = row[3]
            cachedip += 1
            break

        if city == 'NO_CITY':
            continue

        if city == '':
            url = "http://ipinfo.io/{}?token=21a1a8a7be196b".format(line)
            response = requests.get(url)
            data = response.json()
            if 'city' in data.keys():
                city = data['city']
                latlng = data['loc'].split(',')
                lat = latlng[0]
                lng = latlng[1]
                sqlConn.execute("INSERT INTO IPTOCITY (ip, lat, lng, city)  VALUES (?, ?, ?, ?)",
                                (ip, lat, lng, city,));
                sqlConn.commit()
                newip += 1
            else:
                city = 'NO_CITY'
                lat = 0
                lng = 0
                sqlConn.execute("INSERT INTO IPTOCITY (ip, lat, lng, city)  VALUES (?, ?, ?, ?)",
                                (ip, lat, lng, city,));
                sqlConn.commit()
                continue

        found = 0
        for key in cityMap:
            if key == city:
                lat, lng, newVerCount, oldVerCount = cityMap[key]
                if oldNew == 1:
                    newVerCount += 1
                else:
                    oldVerCount += 1
                cityMap[key] = lat, lng, newVerCount, oldVerCount
                found = 1
                break

        if found == 0:
            if oldNew == 1:
                cityMap[city] = [lat, lng, 1, 0]
            else:
                cityMap[city] = [lat, lng, 0, 1]


total = 0
new = 0
cached = 0
cityHashMap = {}
conn = sqlite3.connect('iptocity.db')
getDetails(NEW_FILE, conn, cityHashMap, total, new, cached, 1)
getDetails(OLD_FILE, conn, cityHashMap, total, new, cached, 0)
conn.close()
for key in cityHashMap:
    counts = "'{}' : [{}, {}, {},{}],".format(key, cityHashMap[key][0], cityHashMap[key][1], cityHashMap[key][2],  cityHashMap[key][3])
    print(counts)

