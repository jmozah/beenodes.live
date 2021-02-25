import os
import sys
import sqlite3
import logging
import flask
from flask import Flask, render_template

app = Flask(__name__)
db_file = ''
html_template_file = ''
latest_date = ''
sql_conn = None
available_dates = dict()
data_dic = dict()
counter_dic = dict()


@app.route("/")
def template_test():
    if not latest_date:
        flask.abort(404)
    city_list = getCityList(latest_date)
    (total_peers, c_peers, d_peers) = getCounters(latest_date)
    return render_template(html_template_file, city_list=city_list, total_peers=total_peers, connected_peers=c_peers, disconnected_peers=d_peers)


@app.route('/history/<yyyy>/<mm>/<dd>/<hh>')
def render_history(yyyy, mm, dd, hh):
    if len(yyyy) != 4 or len(mm) != 2 or len(dd) != 2 or len(hh) != 2:
        flask.abort(404)
    requested_date = yyyy + '-' + mm + '-' + dd + '-' + hh
    city_list = getCityList(requested_date)
    (total_peers, c_peers, d_peers) = getCounters(requested_date)
    return render_template(html_template_file, city_list=city_list, total_peers=total_peers, connected_peers=c_peers, disconnected_peers=d_peers)


@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html.template', title='404'), 404


def getCityList(date_str):
    global data_dic
    global sql_conn
    city_list = dict()
    if date_str in data_dic:
        city_list = data_dic[date_str]
    else:
        cursor = sql_conn.execute('select CITY, LAT, LNG, C_COUNT, D_COUNT from CITYBATCH where DATE = ?',(date_str,))
        for row in cursor:
            city = row[0]
            lat = row[1]
            lng = row[2]
            c_count = row[3]
            d_count = row[4]
            line = "'{}' : [ {}, {}, {}, {} ],".format(city, lat, lng, c_count, d_count)
            line = line.rstrip('\n')
            city_list[line] = ''
    return city_list

def getCounters(date_str):
    global counter_dic
    global sql_conn
    total_peers = 0
    c_peers = 0
    d_peers = 0
    if date_str in counter_dic:
        (total_peers, c_peers, d_peers) = counter_dic[date_str]
    else:
        cursor = sql_conn.execute('select TOTAL_PEERS, CONNECTED_PEERS, DISCONNECTED_PEERS from COUNTERS where DATE = ? limit 1', (date_str,))
        for row in cursor:
            total_peers = row[0]
            c_peers = row[1]
            d_peers = row[2]
        counter_dic[date_str] = (total_peers, c_peers, d_peers)
    return total_peers, c_peers, d_peers


def getAllDatesFromDB():
    global latest_date
    global available_dates
    global sql_conn
    try:
        cursor = sql_conn.execute('select DATE from CITYBATCH group by DATE order by DATE asc')
        for row in cursor:
            latest_date = row[0]
            available_dates[latest_date] = ''
        logging.info('got {} dates from DB. latest date is {}'.format(str(len(available_dates)), latest_date))
    except sqlite3.OperationalError as e:
        logging.error('error getting processed dates: {}'.format(e))


def open_sql_conn():
    global sql_conn
    if sql_conn is None:
        try:
            sql_conn = sqlite3.connect(db_file, check_same_thread=False)
        except sqlite3.OperationalError as e:
            logging.error('error opening database: {}'.format(e))
            sys.exit()
        logging.info('opened database file {} successfully'.format(db_file))


def main():
    global db_file
    global html_template_file
    global available_dates
    global sql_conn
    port = ''
    logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s', level=logging.INFO,
                        datefmt='%Y-%m-%d %H:%M:%S')

    if len(sys.argv) == 4:
        db_file = sys.argv[1]
        html_template_file = sys.argv[2]
        port = sys.argv[3]
    else:
        logging.error('python3 serve_nodes.py <dbFileWithPath> <htmlTemplateFileWithPath> <port>')
        sys.exit()

    # check if the db is present
    if not os.path.isfile(db_file):
        logging.error('db file {} not present'.format(db_file))
        sys.exit()

    # open the DB connection
    open_sql_conn()

    # get historic DBs
    getAllDatesFromDB()

    # start the server
    app.run(port=port, debug=True)

    # close database
    if sql_conn is not None:
        sql_conn.close()

if __name__ == "__main__":
    main()
