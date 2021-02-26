import os
import sys
import logging
import sqlite3
import requests
import subprocess
from datetime import datetime, timedelta

max_retry_for_failure = 48

total_peers = 0
c1_peers = 0
c2_peers = 0
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
        logging.info('processing peers in bin {}'.format(bin_name))
        disc_peers = bin['disconnectedPeers']
        connected_peers = bin['connectedPeers']
        if disc_peers is None:
            logging.info('zero disconnected peers in bin {}'.format(bin_name))
            continue
        logging.info('{} disconnected peers in bin {}'.format(str(len(disc_peers)), bin_name))
        for peer in disc_peers:
            inactive_overlays[peer] = ''
            total_peers += 1
        if connected_peers is None:
            logging.info('zero connected peers in bin {}'.format(bin_name))
            continue
        logging.info('{} connected peers in bin {}'.format(str(len(connected_peers)), bin_name))
        for peer in connected_peers:
            active_overlays[peer] = ''
            total_peers += 1
    logging.info(
        'got total of {} connected peers and {} disconnected peers from crawler'.format(str(len(active_overlays)),
                                                                                        str(len(inactive_overlays))))
    return active_overlays, inactive_overlays


def getIPAndPortAndNotResponseCount(sql_conn, peer, log_peers_ip_port):
    global new_peers
    global new_ips
    global err_selecting_ip
    global err_inserting_ip
    global err_no_ip
    ip = ''
    port = 0
    not_response_count = 0
    responding_count = 0
    try:
        cursor = sql_conn.execute(
            'select IP, PORT, NOT_RESPONDING, RESPONDING from OVERLAYIPPORT where OVERLAY = ?  limit 1', (peer,))
        for row in cursor:
            ip = row[0].rstrip('\n')
            port = row[1]
            not_response_count = row[2]
            responding_count = row[3]
            logging.info(
                'got ip={}, port={}, not_responding_count={}, responding_count={} from OVERLAYIPPORT'.format(ip, port,
                                                                                                             not_response_count,
                                                                                                             responding_count, ))
            if not ip:
                sql_conn.execute('delete from OVERLAYIPPORT where OVERLAY = ?', (peer,))
                sql_conn.commit()
                logging.error('deleting empty peer {}'.format(peer))
    except sqlite3.OperationalError as e:
        logging.error('error getting IP from OVERLAYIPPORT for peer {}: {}'.format(peer, e))
        err_selecting_ip += 1
    if not ip:
        new_peers += 1
        if peer in log_peers_ip_port:
            (ip, port) = log_peers_ip_port[peer]
            if ip == "127.0.0.1":
                ip = ''
                port = 0
                not_response_count = 0
                responding_count = 0
                logging.error('ignoring ip for peer {} as it is localhost'.format(peer))
            else:
                try:
                    sql_conn.execute(
                        'insert into OVERLAYIPPORT (OVERLAY, IP, PORT, NOT_RESPONDING, RESPONDING)  values(?, ?, ?, ?, ?)',
                        (peer, ip, port, not_response_count, responding_count))
                    sql_conn.commit()
                    new_ips += 1
                    logging.info('inserting the log harvested ip={} and port={} in to OVERLAYIPPORT'.format(ip, port))
                except sqlite3.OperationalError as e:
                    logging.error('error inserting IP {} into OVERLAYIPPORT for peer {}: {}'.format(ip, peer, e))
                    err_inserting_ip += 1
    if not ip:
        err_no_ip += 1
    return ip, port, not_response_count, responding_count


def getIPPortFromLog(log_today_str, log_yesterday_str, crawler_log):
    log_peers_ip_port = dict()
    logging.info(
        'harvesting successfully connected ips from log for {} and {}'.format(log_today_str, log_yesterday_str))
    commandStr = 'grep "successfully connected to peer" {} | grep "{}\|{}" |  grep ip4 | cut -d " " -f8,10 |tr -d " " | tr -d "," | cut -d "/" -f1,3,5 | sort | uniq'.format(
        crawler_log, log_today_str, log_yesterday_str)
    result = subprocess.check_output(commandStr, shell=True)
    lines = result.decode('utf-8')
    if not lines:
        logging.info('could not harvest any ips from success log')
    else:
        rows = lines.split('\n')
        for line in rows:
            cols = line.split("/")
            if len(cols) == 3:
                log_peers_ip_port[cols[0]] = (cols[1], cols[2])
        logging.info('harvested {} ips from successfully connected log'.format(str(len(log_peers_ip_port))))

    logging.info(
        'harvesting not reachable ips from log for {} and {}'.format(log_today_str, log_yesterday_str))
    commandStr = 'grep "peer not reachable from kademlia" {} | grep "{}\|{}" | grep ip4 | cut -d " " -f9,11 | tr -d " " | tr  "," "/" | cut -d "/" -f3,5,8 | sort | uniq'.format(
        crawler_log, log_today_str, log_yesterday_str)
    result = subprocess.check_output(commandStr, shell=True)
    lines = result.decode('utf-8')
    if not lines:
        logging.info('could not harvest any ips from not reachable log')
        return log_peers_ip_port
    else:
        rows = lines.split('\n')
        for line in rows:
            cols = line.split("/")
            if len(cols) == 3:
                log_peers_ip_port[cols[2]] = (cols[0], cols[1])
        logging.info('harvested {} ips from not connected log'.format(str(len(log_peers_ip_port))))

    return log_peers_ip_port


def getCity(sql_conn, ip):
    global new_citys
    global err_selecting_city
    global err_inserting_city
    global err_no_city
    lat = ''
    lng = ''
    city = ''
    if not ip:
        return lat, lng, city
    try:
        cursor = sql_conn.execute('select LAT, LNG, CITY from IPTOCITY where IP = ? limit 1', (ip,))
        for row in cursor:
            lat = row[0]
            lng = row[1]
            city = row[2].rstrip('\n')
        logging.info('city info for ip={} got from IPTOCITY'.format(ip))
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
                logging.info('city info for ip={} got from ipinfo city={}, lat={], lng={}'.format(ip, city, lat, lng))
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


def addToCityCount(city_count, city, lat, lng, green_count, orange_count, red_count):
    if city in city_count.keys():
        la, ln, green, orange, red = city_count[city]
        green = green + green_count
        orange = orange + orange_count
        red = red + red_count
        city_count[city] = la, ln, green, orange, red
    else:
        city_count[city] = lat, lng, green_count, orange_count, red_count


def insertCityCountsToTable(sql_conn, city_count, date_str):
    global total_rows_in_this_batch
    global err_inserting_citybatch
    for city in city_count:
        la, ln, green_count, orange_count, red_count = city_count[city]
        if not city or city == 'null':
            continue
        try:
            sql_conn.execute(
                'insert into CITYBATCH (DATE, LAT, LNG, CITY, GREEN_COUNT, ORANGE_COUNT, RED_COUNT)  values (?, ?, ?, ?, ?, ?, ?)',
                (date_str, la, ln, city, green_count, orange_count, red_count))
            sql_conn.commit()
            total_rows_in_this_batch += 1
        except sqlite3.OperationalError as e:
            logging.error('error inserting into CITYBATCH: {}'.format(e))
            err_inserting_citybatch += 1
            return
    logging.info('added {} rows in this batch'.format(str(total_rows_in_this_batch)))


def addCounters(sql_conn, date_str):
    try:
        sql_conn.execute(
            'insert into COUNTERS (DATE, TOTAL_PEERS, CONNECTED_PEERS, CONNECTED_FOUND_PEERS, DISCONNECTED_PEERS, NEW_PEERS, NEW_IPS, NEW_CITIS, TOTAL_ROWS_IN_BATCH, ERR_SELECTING_IP, ERR_INSERTING_IP, ERR_NOIP, ERR_SELECTING_CITY, ERR_INSERTING_CITY, ERR_NOCITY, ERR_INSERTING_CITYBATCH)  values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (
            date_str, total_peers, c1_peers, c2_peers, d_peers, new_peers, new_ips, new_citys, total_rows_in_this_batch,
            err_selecting_ip, err_inserting_ip, err_no_ip, err_selecting_city, err_inserting_city, err_no_city,
            err_inserting_citybatch))
        sql_conn.commit()
        logging.info('date                     = {} '.format(date_str))
        logging.info('total_peers              = {} '.format(str(total_peers)))
        logging.info('connected_peers          = {} '.format(str(c1_peers)))
        logging.info('connected_peers (ping)   = {} '.format(str(c2_peers)))
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


def getIPPortLatLngCity(sql_conn, peer, log_peers_ip_port):
    ip, port, not_response_count, responding_count = getIPAndPortAndNotResponseCount(sql_conn, peer, log_peers_ip_port)
    lat, lng, city = getCity(sql_conn, ip)
    return ip, port, not_response_count, responding_count, lat, lng, city


def main():
    global c1_peers
    global c2_peers
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

    today = datetime.now()
    yesterday = datetime.now() - timedelta(1)
    date_str = today.strftime("%Y-%m-%d-%H")
    log_today_str = today.strftime("%Y-%m-%dT")
    log_yesterday_str = yesterday.strftime("%Y-%m-%dT")
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

    # check if lock is open, then start processing
    pid = str(os.getpid())
    pidfile = "/tmp/beenodes.pid"
    if os.path.isfile(pidfile):
        print(" {} already exists, exiting".format(pidfile))
        sys.exit()

    open(pidfile, "w+").write(pid)
    try:
        log_peers_ip_port = getIPPortFromLog(log_today_str, log_yesterday_str, crawler_logs)

        # get the connected and disconnected peers from the crawler
        connected_peers, disconnected_peers = getPeersFromCrawler(url)

        # harvest IP for the connected overlays
        for peer in connected_peers:
            c1_peers += 1
            logging.info('processing connected peer {}'.format(peer))
            ip, port, not_response_count, responding_count, lat, lng, city = getIPPortLatLngCity(sql_conn, peer,
                                                                                                 log_peers_ip_port)
            if not ip:
                logging.error('could not proceed with {} as IP could not be found'.format(peer))
                continue
            if city == 'NOCITY':
                logging.error('could not proceed with {} as CITY could not be found'.format(peer))
                continue
            addToCityCount(city_counts, city, lat, lng, 1, 0, 0)
            # increment the responding count and make not-responding as 0
            not_response_count = 0
            responding_count += 1
            sql_conn.execute('update OVERLAYIPPORT SET NOT_RESPONDING = ?, RESPONDING = ? WHERE OVERLAY = ?',
                             (not_response_count, responding_count, peer,))
            sql_conn.commit()

        # harvest IP for the disconnected overlays
        for peer in disconnected_peers:
            logging.info('processing disconnected peer {}'.format(peer))
            ip, port, not_response_count, responding_count, lat, lng, city = getIPPortLatLngCity(sql_conn, peer,
                                                                                                 log_peers_ip_port)
            if not ip:
                logging.error('could not proceed with {} as IP could not be found'.format(peer))
                continue
            if city == 'NOCITY':
                logging.error('could not proceed with {} as CITY could not be found'.format(peer))
                continue
            if not_response_count < max_retry_for_failure:
                addToCityCount(city_counts, city, lat, lng, 0, 1, 0)
            else:
                addToCityCount(city_counts, city, lat, lng, 0, 0, 1)
            responding_count = 0
            not_response_count += 1
            sql_conn.execute('update OVERLAYIPPORT SET NOT_RESPONDING = ?, RESPONDING = ? WHERE OVERLAY = ?',
                             (not_response_count, responding_count, peer,))
            sql_conn.commit()

        # Insert the batch data in to CITYBATCH table
        insertCityCountsToTable(sql_conn, city_counts, date_str)

        # add the counters
        addCounters(sql_conn, date_str)
    finally:
        os.unlink(pidfile)
        logging.info('removed lock and exiting')


if __name__ == "__main__":
    main()
