import os
import sys
import logging
import sqlite3
import requests
from datetime import datetime

def getIPAndPortAndPeersCountFromCrawlerDB(crawler_sql_conn):
    ip_info = dict()
    try:
        cursor = crawler_sql_conn.execute('select IP, PORT, PEERS_COUNT from PEER_INFO')
        for row in cursor:
            ip = row[0].rstrip('\n')
            port = row[1]
            peers_count = row[2]
            key = ip + str(port)
            ip_info[key] = (ip, port, peers_count)
    except sqlite3.OperationalError as e:
        logging.error('error getting IP, PORT and PEERS_COUNT from PEER_INFO : {}'.format(e))
    logging.info('got {} peers from PEER_INFO'.format(str(len(ip_info))))
    return ip_info


def getLatLngCityFromIP(beenodes_sql_conn, ip):
    lat = ''
    lng = ''
    city = ''
    if not ip:
        return lat, lng, city
    try:
        cursor = beenodes_sql_conn.execute('select LAT, LNG, CITY from IP_INFO where IP = ? limit 1', (ip,))
        for row in cursor:
            lat = row[0]
            lng = row[1]
            city = row[2].rstrip('\n')
    except sqlite3.OperationalError as e:
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
            try:
                beenodes_sql_conn.execute('insert into IP_INFO (ip, lat, lng, city)  values (?, ?, ?, ?)',
                                 (ip, lat, lng, city,))
                beenodes_sql_conn.commit()
                logging.info('city info for ip={} got from ipinfo city={}, lat={}, lng={}'.format(ip, city, lat, lng))
            except sqlite3.OperationalError as e:
                logging.error('error inserting city into IPTOCITY for IP {}: {}'.format(ip, e))
        else:
            city = 'NOCITY'
    return lat, lng, city


def checkIfBatchDone(sql_conn, batch_id):
    id = ''
    try:
        cursor = sql_conn.execute('select BATCH from CITY_INFO where BATCH = ? limit 1', (batch_id,))
        for row in cursor:
            id = row[0]
    except sqlite3.OperationalError as e:
        logging.error('error checking if this batch is processed already: {}'.format(e))
    return id


def addToCityCount(city_count, city, lat, lng, green_count, orange_count, red_count):
    if city in city_count.keys():
        la, ln, green, orange, red = city_count[city]
        green = green + green_count
        orange = orange + orange_count
        red = red + red_count
        city_count[city] = la, ln, green, orange, red
    else:
        city_count[city] = lat, lng, green_count, orange_count, red_count


def insertCityCountsToTable(beenodes_sql_conn, city_count, batch_id):
    total_rows_in_this_batch = 0
    for city in city_count:
        la, ln, green_count, orange_count, red_count = city_count[city]
        if not city or city == 'null':
            continue
        try:
            beenodes_sql_conn.execute(
                'insert into CITY_INFO (BATCH, CITY, LAT, LNG, GREEN_COUNT, ORANGE_COUNT, RED_COUNT)  values (?, ?, ?, ?, ?, ?, ?)',
                (batch_id, city, la, ln, green_count, orange_count, red_count))
            total_rows_in_this_batch += 1
        except sqlite3.OperationalError as e:
            logging.error('error inserting into CITYBATCH: {}'.format(e))
            beenodes_sql_conn.commit()
            return
    beenodes_sql_conn.commit()
    logging.info('added {} rows in this batch'.format(str(total_rows_in_this_batch)))

def main():
    city_counts = dict()
    logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s', level=logging.INFO,
                        datefmt='%Y-%m-%d %H:%M:%S')

    if len(sys.argv) == 3:
        beenodeslive_db_file = sys.argv[1]
        crawler_db_file = sys.argv[2]
    else:
        logging.error('python3 update_index.py <beenodesDBFileWithPath> <crawlerDBFileWithPath>')
        sys.exit()

    today = datetime.now()
    batch_id = today.strftime("%Y-%m-%d-%H-%M")
    logging.info('Starting update_index for batch id {}'.format(batch_id))

    # check if the beenodes db is present
    if not os.path.isfile(beenodeslive_db_file):
        logging.error('db file {} not present'.format(beenodeslive_db_file))
        sys.exit()

    # check if the crawler db is present
    if not os.path.isfile(crawler_db_file):
        logging.error('db file {} not present'.format(crawler_db_file))
        sys.exit()


    # open the beenodes DB
    try:
        beenodes_sql_conn = sqlite3.connect(beenodeslive_db_file)
    except sqlite3.OperationalError as e:
        logging.error('error opening beenodes database: {}'.format(e))
        sys.exit()

    # check if this date is already processed
    if checkIfBatchDone(beenodes_sql_conn, batch_id):
        logging.error("this batch is already processed")
        sys.exit()

    # open the crawler DB
    try:
        crawler_sql_conn = sqlite3.connect(crawler_db_file)
        ip_info = getIPAndPortAndPeersCountFromCrawlerDB(crawler_sql_conn)
        crawler_sql_conn.close()
    except sqlite3.OperationalError as e:
        logging.error('error opening crawler database: {}'.format(e))
        beenodes_sql_conn.close()
        sys.exit()


    # check if lock is open, then start processing
    pid = str(os.getpid())
    pidfile = "/tmp/beenodes.pid"
    if os.path.isfile(pidfile):
        print(" {} already exists, exiting".format(pidfile))
        beenodes_sql_conn.close()
        sys.exit()

    open(pidfile, "w+").write(pid)
    try:
        for key in ip_info:
            (ip, port, peers_count) = ip_info[key]
            lat, lng, city = getLatLngCityFromIP(beenodes_sql_conn, ip)
            if city == 'NOCITY':
                logging.error('could not proceed with {} as CITY could not be found'.format(ip))
                continue
            if peers_count < 0:
                addToCityCount(city_counts, city, lat, lng, 0, 1, 0)
            if peers_count >= 0:
                addToCityCount(city_counts, city, lat, lng, 1, 0, 0)

        # Insert the batch data in to CITYBATCH table
        insertCityCountsToTable(beenodes_sql_conn, city_counts, batch_id)

    finally:
        beenodes_sql_conn.close()
        os.unlink(pidfile)
        logging.info('removed lock and exiting')


if __name__ == "__main__":
    main()
