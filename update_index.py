import os
import sys
import logging
import requests
import pycountry
import mysql.connector
from pathlib import Path
from datetime import datetime

def checkIfBatchDone(sql_conn, batch_id):
    id = ''
    sql_cursor = sql_conn.cursor()
    try:
        sql_cursor.execute("select BATCH from CITY_INFO where BATCH=%s", (batch_id,))
        result = sql_cursor.fetchone()
        if result:
            id = result[0]
    except Exception as e:
        logging.error('error checking if this batch is processed already: {}'.format(e))
    finally:
        sql_cursor.close()
        return id


def getIPAndPortAndPeersCountFromCrawlerDB(sql_conn):
    ip_info = dict()
    sql_cursor = sql_conn.cursor()
    try:
        sql_cursor.execute("select IP, PORT, CONNECTED from PEER_INFO")
        result = sql_cursor.fetchall()
        for row in result:
            ip = row[0].rstrip('\n')
            port = row[1]
            connected = row[2]
            key = ip + str(port)
            ip_info[key] = (ip, port, connected)
    except Exception as e:
        logging.error('error getting IP, PORT and PEERS_COUNT from PEER_INFO : {}'.format(e))
    finally:
        sql_cursor.close()
        return ip_info


def getLatLngCityFromIP(sql_conn, ip):
    lat = ''
    lng = ''
    city = ''
    if not ip:
        return lat, lng, city
    sql_cursor = sql_conn.cursor()
    try:
        sql_cursor.execute("select LAT, LNG, CITY from IP_INFO where IP=%s", (ip,))
        result = sql_cursor.fetchone()
        if result:
            lat = result[0]
            lng = result[1]
            city = result[2].rstrip('\n')
    except Exception as e:
        logging.error('error getting city from IPTOCITY for IP {}: {}'.format(ip, e))

    if not city:
        url = "http://ipinfo.io/{}?token=21a1a8a7be196b".format(ip)
        response = requests.get(url)
        data = response.json()
        if 'city' in data.keys():
            city = data['city']
            latlng = data['loc'].split(',')
            lat = latlng[0]
            lng = latlng[1]
            country = ''
            asn = ''
            org = ''
            isp = ''
            if 'country' in data.keys():
                country = data['country']
            if 'asn' in data.keys():
                asn = data['asn']['asn']
                org = data['asn']['name']
                isp = data['asn']['type']
            fc = pycountry.countries.get(alpha_2=country)
            if hasattr(fc, 'official_name'):
                full_country = fc.official_name
            elif hasattr(fc, 'name'):
                full_country = fc.name
            else:
                full_country = country
            try:
                sql_cursor.execute("insert into IP_INFO (ip, lat, lng, city, country, asn, organisation, isp)  values (%s, %s, %s, %s, %s, %s, %s, %s)",
                                 (ip, lat, lng, city, full_country, asn, org, isp))
                sql_conn.commit()
                logging.info('city info for ip={} got from ipinfo city={}, lat={}, lng={}'.format(ip, city, lat, lng))
            except Exception as e:
                logging.error('error inserting city into IPTOCITY for IP {}: {}'.format(ip, e))

        else:
            lat = '0.00'
            lng = '0.00'
            city = 'NO_CITY'
            full_country = 'NO_COUNTRY'
            asn = 'NO_ASN'
            org = 'NO_ORG'
            isp = 'NO_ISP'
            sql_cursor.execute(
                "insert into IP_INFO (ip, lat, lng, city, country, asn, organisation, isp)  values (%s, %s, %s, %s, %s, %s, %s, %s)",
                (ip, lat, lng, city, full_country, asn, org, isp))
            sql_conn.commit()
            logging.error('inserting no_city into IPTOCITY for IP {}'.format(ip))
    sql_cursor.close()
    return lat, lng, city




def addToCityCount(city_count, city, lat, lng, green_count, orange_count, red_count):
    if city in city_count.keys():
        la, ln, green, orange, red = city_count[city]
        green = green + green_count
        orange = orange + orange_count
        red = red + red_count
        city_count[city] = la, ln, green, orange, red
    else:
        city_count[city] = lat, lng, green_count, orange_count, red_count


def insertCityCountsToTable(sql_conn, city_count, batch_id):
    total_rows_in_this_batch = 0
    for city in city_count:
        la, ln, green_count, orange_count, red_count = city_count[city]
        if not city or city == 'null':
            continue
        sql_cursor = sql_conn.cursor()
        try:
            sql_cursor.execute(
                'insert into CITY_INFO (BATCH, CITY, LAT, LNG, GREEN_COUNT, ORANGE_COUNT, RED_COUNT)  values (%s, %s, %s, %s, %s, %s, %s)',
                (batch_id, city, la, ln, green_count, orange_count, red_count),)
            total_rows_in_this_batch += 1
            sql_conn.commit()
        except Exception as e:
            logging.error('error inserting into CITYBATCH: {}'.format(e))
        finally:
            sql_cursor.close()

    logging.info('added {} rows in this batch'.format(str(total_rows_in_this_batch)))

def main():
    city_counts = dict()
    logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s', level=logging.INFO,
                        datefmt='%Y-%m-%d %H:%M:%S')

    home = str(Path.home())
    db_password_file = home + '/bin/dbpwd'
    file = open(db_password_file, mode='r')
    dbPassword = file.read()
    dbPassword = dbPassword.rstrip('\n')
    file.close()

    today = datetime.now()
    batch_id = today.strftime("%Y-%m-%d-%H-%M")
    logging.info('Starting update_index for batch id {}'.format(batch_id))

    # open the beenodes DB
    try:
        sql_conn = mysql.connector.connect(
            host="localhost",
            user="crawler",
            password=dbPassword,
            database="crawler"
        )
    except Exception as e:
        logging.error('error opening database: {}'.format(e))
        sys.exit()

    # check if this date is already processed
    if checkIfBatchDone(sql_conn, batch_id):
        logging.error("this batch is already processed")
        sys.exit()

    # check if lock is open, then start processing
    pid = str(os.getpid())
    pidfile = "/tmp/beenodes.pid"
    if os.path.isfile(pidfile):
        print(" {} already exists, exiting".format(pidfile))
        sys.exit()

    open(pidfile, "w+").write(pid)
    try:

        # load the ip info
        ip_info = getIPAndPortAndPeersCountFromCrawlerDB(sql_conn)

        for key in ip_info:
            (ip, port, connected) = ip_info[key]
            lat, lng, city = getLatLngCityFromIP(sql_conn, ip)
            if city == 'NOCITY':
                logging.error('could not proceed with {} as CITY could not be found'.format(ip))
                addToCityCount(city_counts, city, 0, 0, 1, 0, 0)
                continue
            if connected == 0:
                addToCityCount(city_counts, city, lat, lng, 0, 1, 0)
            if connected == 1:
                addToCityCount(city_counts, city, lat, lng, 1, 0, 0)

        # Insert the batch data in to CITYBATCH table
        insertCityCountsToTable(sql_conn, city_counts, batch_id)

    finally:
        sql_conn.close()
        os.unlink(pidfile)
        logging.info('removed lock and exiting')


if __name__ == "__main__":
    main()
