import os
import sys
import sqlite3
import logging
import flask
from pathlib import Path
from flask import Flask, render_template
from flask_caching import Cache


config = {
    "DEBUG": True,
    "CACHE_TYPE": "SimpleCache",
    "CACHE_DEFAULT_TIMEOUT": 1000
}

app = Flask(__name__)
app.config.from_mapping(config)
cache = Cache(app)

html_template_file = 'index.html.template'

latest_batch = None
sql_conn = None
available_batches = dict()
batch_dic = dict()
counter_dict= dict()

@app.route("/")
@cache.cached(timeout=1000)
def render_root():
    global latest_batch
    global available_batches
    global sql_conn

    if sql_conn is None:
        open_sql_conn()
    if latest_batch is None:
        getAllDatesFromDB()

    city_list, total_peers, connected_peers, disconnected_peers = getCityList(latest_batch)
    cols = latest_batch.split('-')
    date_string = cols[0] + '/' + cols[1] + '/' + cols[2] + ' - ' + cols[3] + ' : ' + cols[4]
    return render_template(html_template_file, city_list=city_list, total_peers=total_peers, connected_peers=connected_peers, disconnected_peers=disconnected_peers, snapshot_time=date_string)


@app.route('/history/<yyyy>/<mm>/<dd>/<hh>/<MM>')
@cache.cached(timeout=50)
def render_history(yyyy, mm, dd, hh, MM):
    global latest_batch
    global sql_conn

    if len(yyyy) != 4 or len(mm) != 2 or len(dd) != 2 or len(hh) != 2 or len(MM) != 2:
        flask.abort(404)
    requested_date = yyyy + '-' + mm + '-' + dd + '-' + hh + '-' + MM

    if sql_conn is None:
        open_sql_conn()
    if latest_batch is None:
        getAllDatesFromDB()

    city_list, total_peers, connected_peers, disconnected_peers = getCityList(requested_date)
    cols = latest_batch.split('-')
    date_string = cols[0] + '/' + cols[1] + '/' + cols[2] + ' - ' + cols[3] + ' : ' + cols[4]
    return render_template(html_template_file, city_list=city_list, total_peers=total_peers, connected_peers=connected_peers, disconnected_peers=disconnected_peers, snapshot_time=date_string)


@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html.template', title='404'), 404


def getCityList(batch_id):
    global batch_dic
    global sql_conn
    total_peers = 0
    connected_peers = 0
    disconnected_peers = 0
    city_list = dict()
    if batch_id in batch_dic:
        city_list = batch_dic[batch_id]
        (total_peers, connected_peers, disconnected_peers) = counter_dict[batch_id]
    else:
        cursor = sql_conn.execute('select CITY, LAT, LNG, GREEN_COUNT, ORANGE_COUNT, RED_COUNT from CITY_INFO where BATCH = ?',(batch_id,))
        for row in cursor:
            city = row[0]
            lat = row[1]
            lng = row[2]
            green_count = row[3]
            orange_count = row[4]
            red_count = row[5]
            city = city.replace("'", "")
            line = "'{}' : [ {}, {}, {}, {} ],".format(city, lat, lng, green_count, orange_count, red_count)
            line = line.rstrip('\n')
            city_list[line] = ''
            total_peers += green_count
            total_peers += orange_count
            total_peers += red_count
            if green_count > 0:
                connected_peers += green_count
            if orange_count > 0:
                disconnected_peers += orange_count
        counter_dict[batch_id] = (total_peers, connected_peers, disconnected_peers)
        batch_dic[batch_id] = city_list
    return city_list , total_peers, connected_peers, disconnected_peers

def getAllDatesFromDB():
    global latest_batch
    global available_batches
    global sql_conn
    try:
        cursor = sql_conn.execute('select BATCH from CITY_INFO group by BATCH order by BATCH asc')
        for row in cursor:
            latest_batch = row[0]
            available_batches[latest_batch] = ''
        logging.info('got {} batches from DB. latest batch is {}'.format(str(len(available_batches)), latest_batch))
    except sqlite3.OperationalError as e:
        logging.error('error getting processed dates: {}'.format(e))


def open_sql_conn():
    global sql_conn

    home = str(Path.home())
    db_file = home + '/.crawler/beenodeslive.db'
    if not os.path.isfile(db_file):
        logging.error('db file {} not present'.format(db_file))
        sys.exit()

    try:
        sql_conn = sqlite3.connect(db_file, check_same_thread=False)
    except sqlite3.OperationalError as e:
        logging.error('error opening database: {}'.format(e))
        sys.exit()
    logging.info('opened database file {} successfully'.format(db_file))


if __name__ == "__main__":
    app.run(host='0.0.0.0')
