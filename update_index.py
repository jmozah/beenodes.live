import os
import sys
import logging
import datetime
import sqlite3
import requests
import subprocess


total_peers = 0
c_peers = 0
d_peers = 0
new_peers = 0
new_ips = 0
new_citys = 0
total_rows_in_this_batch = 0

err_selecting_ip = 0
err_inserting_ip = 0
err_no_ip = 0
err_selecting_city = 0
err_inserting_city = 0
err_no_city = 0
err_inserting_citybatch = 0


def getPeersFromCrawler(url):
    global total_peers
    active_overlays = dict()
    inactive_overlays = dict()

    logging.info("getting peers from crawler")
    response = requests.get(url)
    topology = response.json()
    bins = topology['bins']
    for bin_name in bins:
        bin = bins[bin_name]
        disc_peers = bin['disconnectedPeers']
        if disc_peers is None:
            continue
        for peer in disc_peers:
            inactive_overlays[peer] = ''
            total_peers += 1
        connected_peers = bin['connectedPeers']
        if connected_peers is None:
            continue
        for peer in connected_peers:
            active_overlays[peer] = ''
            total_peers += 1
    logging.info('got {} connected peers and {} disconnected peers from crawler'.format(str(len(active_overlays)), str(len(inactive_overlays))))
    return active_overlays, inactive_overlays


def getIP(sql_conn, peer, log_peers_and_ip):
    global new_peers
    global new_ips
    global err_selecting_ip
    global err_inserting_ip
    global err_no_ip
    ip = ''
    try:
        cursor = sql_conn.execute('select IP from OVERLAYTOIP where OVERLAY = ?  limit 1', (peer,))
        for row in cursor:
            ip = row[0].rstrip('\n')
        if not ip:
            sql_conn.execute('delete from OVERLAYTOIP where OVERLAY = ?', (peer,))
            sql_conn.commit()
            logging.error('deleting empty peer {}'.format(peer))
    except sqlite3.OperationalError as e:
        logging.error('error getting IP from OVERLAYTOIP for peer {}: {}'.format(peer, e))
        err_selecting_ip += 1
    if not ip:
        new_peers += 1
        if ip in log_peers_and_ip:
            ip = log_peers_and_ip[peer]
            if ip == "127.0.0.1":
                ip = ''
            else:
                try:
                    sql_conn.execute('insert into OVERLAYTOIP (OVERLAY, IP)  values(?, ?)', (peer, ip))
                    sql_conn.commit()
                    new_ips += 1
                except sqlite3.OperationalError as e:
                    logging.error('error inserting IP {} into OVERLAYTOIP for peer {}: {}'.format(ip, peer, e))
                    err_inserting_ip += 1
    if not ip:
        err_no_ip += 1
    return ip


def getIPFromLog(log_date_str, crawler_log):
    log_peers_and_ip = dict()
    logging.info('harvesting ips from log for {}'.format(log_date_str))
    commandStr = 'grep "successfully connected to peer\|peer not reachable from kademlia" {} | grep {} |  grep ip4 | tr -s " " | cut -d " " -f8,10 | tr -d " " | tr -d "," | cut -d "/" -f1,3 | sort | uniq'.format(
        crawler_log, log_date_str)
    result = subprocess.check_output(commandStr, shell=True)
    lines = result.decode('utf-8')
    if not lines:
        logging.info('could not harvest any ips from log')
        return log_peers_and_ip
    rows = lines.split('\n')
    for line in rows:
        cols = line.split("/")
        if len(cols) == 2:
            log_peers_and_ip[cols[0]] = cols[1]
    logging.info('harvested {} ips from log'.format(str(len(log_peers_and_ip))))
    return log_peers_and_ip

def getCity(sql_conn, ip):
    global new_citys
    global err_selecting_city
    global err_inserting_city
    global err_no_city
    lat = ''
    lng = ''
    city = ''
    try:
        cursor = sql_conn.execute('select LAT, LNG, CITY from IPTOCITY where IP = ? limit 1', (ip,))
        for row in cursor:
            lat = row[0]
            lng = row[1]
            city = row[2].rstrip('\n')
    except sqlite3.OperationalError as e:
        logging.error('error getting city from IPTOCITY for IP {}: {}'.format(ip, e))
        err_selecting_city += 1
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
                sql_conn.execute('insert into IPTOCITY (ip, lat, lng, city)  values (?, ?, ?, ?)',
                                 (ip, lat, lng, city,))
                sql_conn.commit()
                new_citys += 0
            except sqlite3.OperationalError as e:
                logging.error('error inserting city into IPTOCITY for IP {}: {}'.format(ip, e))
                err_inserting_city += 1
        else:
            city = 'NOCITY'
            err_no_city += 1
    return lat, lng, city


def checkIfHourDone(sql_conn, date_str):
    id = ''
    try:
        cursor = sql_conn.execute('select ID from CITYBATCH where DATE = ? limit 1', (date_str,))
        for row in cursor:
            id = row[0]
    except sqlite3.OperationalError as e:
        logging.error('error checking if this hour is processed already: {}'.format(e))
    return id


def addToCityCount(city_count, city, lat, lng, c_count, d_count):
    if city in city_count.keys():
        la, ln, c1, d1 = city_count[city]
        c1 = c1 + c_count
        d1 = d1 + d_count
        city_count[city] = la, ln, c1, d1
    else:
        city_count[city] = lat, lng, c_count, d_count


def insertCityCountsToTable(sql_conn, city_count, date_str):
    global total_rows_in_this_batch
    global err_inserting_citybatch
    for city in city_count:
        la, ln, c1, d1 = city_count[city]
        if not city or city == 'null':
            continue
        try:
            sql_conn.execute('insert into CITYBATCH (DATE, LAT, LNG, CITY, C_COUNT, D_COUNT)  values (?, ?, ?, ?, ?, ?)', (date_str, la, ln, city, c1, d1))
            sql_conn.commit()
            total_rows_in_this_batch += 1
        except sqlite3.OperationalError as e:
            logging.error('error inserting into CITYBATCH: {}'.format(e))
            err_inserting_citybatch += 1
            return
    logging.info('added {} rows in this batch'.format(str(total_rows_in_this_batch)))

def addCounters(sql_conn, date_str):
    try:
        sql_conn.execute('insert into COUNTERS (DATE, TOTAL_PEERS, CONNECTED_PEERS, DISCONNECTED_PEERS, NEW_PEERS, NEW_IPS, NEW_CITIS, TOTAL_ROWS_IN_BATCH, ERR_SELECTING_IP, ERR_INSERTING_IP, ERR_NOIP, ERR_SELECTING_CITY, ERR_INSERTING_CITY, ERR_NOCITY, ERR_INSERTING_CITYBATCH)  values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                         (date_str, total_peers, c_peers, d_peers, new_peers, new_ips, new_citys, total_rows_in_this_batch, err_selecting_ip, err_inserting_ip, err_no_ip, err_selecting_city, err_inserting_city, err_no_city, err_inserting_citybatch))
        sql_conn.commit()
        logging.info('date                     = {} '.format(date_str))
        logging.info('total_peers              = {} '.format(str(total_peers)))
        logging.info('connected_peers          = {} '.format(str(c_peers)))
        logging.info('disconnected_peers       = {} '.format(str(d_peers)))
        logging.info('new_peers                = {} '.format(str(new_peers)))
        logging.info('new_ips                  = {} '.format(str(new_ips)))
        logging.info('new_citys                = {} '.format(str(new_citys)))
        logging.info('total_rows_in_this_batch = {} '.format(str(total_rows_in_this_batch)))
        logging.info('err_selecting_ip         = {} '.format(str(err_selecting_ip)))
        logging.info('err_inserting_ip         = {} '.format(str(err_inserting_ip)))
        logging.info('err_no_ip                = {} '.format(str(err_no_ip)))
        logging.info('err_selecting_city       = {} '.format(str(err_selecting_city)))
        logging.info('err_inserting_city       = {} '.format(str(err_inserting_city)))
        logging.info('err_no_city              = {} '.format(str(err_no_city)))
        logging.info('err_inserting_citybatch  = {} '.format(str(err_inserting_citybatch)))
    except sqlite3.OperationalError as e:
        logging.error('error inserting into COUNTERS: {}'.format(e))



def main():
    global c_peers
    global d_peers
    db_file = ''
    crawler_logs = ''
    url = ''
    city_counts = dict()
    logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s', level=logging.INFO,
                        datefmt='%Y-%m-%d %H:%M:%S')

    if len(sys.argv) == 4:
        db_file = sys.argv[1]
        crawler_logs = sys.argv[2]
        url = sys.argv[3] + '/topology'
    else:
        logging.error('python3 update_index.py <dbFileWithPath> <crawlerLogs> <crawlerDebugAPIUrl>')
        sys.exit()

    dt = datetime.datetime.now()
    date_str = dt.strftime("%Y-%m-%d-%H")
    log_date_str = dt.strftime("%Y-%m-%dT")
    logging.info('Starting update_index for {}'.format(date_str))

    # check if the db is present
    if not os.path.isfile(db_file):
        logging.error('db file {} not present'.format(db_file))
        sys.exit()

    # open the DB file
    try:
        sql_conn = sqlite3.connect(db_file)
    except sqlite3.OperationalError as e:
        logging.error('error opening database: {}'.format(e))
        sys.exit()

    # check if this date is already processed
    if checkIfHourDone(sql_conn, date_str):
        logging.error("this hour is already processed")
        sys.exit()


    log_peers_and_ip = getIPFromLog(log_date_str, crawler_logs)


    # get the connected and disconnected peers from the crawler
    connected_peers, disconnected_peers = getPeersFromCrawler(url)

    # harvest IP for the connected overlays
    for peer in connected_peers:
        logging.info('processing connected peer {}'.format(peer))
        c_peers += 1
        ip = getIP(sql_conn, peer, log_peers_and_ip)
        if not ip:
            logging.error('could not proceed with {} as IP could not be found'.format(peer))
            continue
        connected_peers[peer] = ip
        lat, lng, city = getCity(sql_conn, ip)
        if city == 'NOCITY':
            logging.error('could not proceed with {} as CITY could not be found'.format(peer))
            continue
        addToCityCount(city_counts, city, lat, lng, 1, 0)

    # harvest IP for the disconnected overlays
    for peer in disconnected_peers:
        d_peers += 1
        logging.info('processing disconnected peer {}'.format(peer))
        ip = getIP(sql_conn, peer, log_peers_and_ip)
        if not ip:
            logging.error('could not proceed with {} as IP could not be found'.format(peer))
            continue
        disconnected_peers[peer] = ip
        lat, lng, city = getCity(sql_conn, ip)
        if city == 'NOCITY':
            logging.error('could not proceed with {} as CITY could not be found'.format(peer))
            continue
        addToCityCount(city_counts, city, lat, lng, 0, 1)

    # Insert the batch data in to CITYBATCH table
    insertCityCountsToTable(sql_conn, city_counts, date_str)

    # add the counters
    addCounters(sql_conn, date_str)

if __name__ == "__main__":
    main()
