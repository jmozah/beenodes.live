import os
import sys
import sqlite3
import logging
import flask
from flask import Flask, render_template

app = Flask(__name__)
db_file = ''
html_template_file = ''
latest_batch = ''
sql_conn = None
available_batches = dict()
batch_dic = dict()
counter_dict= dict()

@app.route("/")
def template_test():
    if not latest_batch:
        flask.abort(404)
    city_list, total_peers, connected_peers, disconnected_peers = getCityList(latest_batch)
    return render_template(html_template_file, city_list=city_list, total_peers=total_peers, connected_peers=connected_peers, disconnected_peers=disconnected_peers)


@app.route('/history/<yyyy>/<mm>/<dd>/<hh>/<MM>')
def render_history(yyyy, mm, dd, hh, MM):
    if len(yyyy) != 4 or len(mm) != 2 or len(dd) != 2 or len(hh) != 2 or len(MM) != 2:
        flask.abort(404)
    requested_date = yyyy + '-' + mm + '-' + dd + '-' + hh + '-' + MM
    city_list, total_peers, connected_peers, disconnected_peers = getCityList(requested_date)
    return render_template(html_template_file, city_list=city_list, total_peers=total_peers, connected_peers=connected_peers, disconnected_peers=disconnected_peers)


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
            line = "'{}' : [ {}, {}, {}, {} ],".format(city, lat, lng, green_count, orange_count, red_count)
            line = line.rstrip('\n')
            city_list[line] = ''
            total_peers += 1
            if green_count > 0:
                connected_peers += 1
            if orange_count > 0:
                disconnected_peers += 1
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
    global sql_conn
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
    app.run(port=port)

    # close database
    if sql_conn is not None:
        sql_conn.Close()

if __name__ == "__main__":
    main()
