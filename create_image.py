import sys
import logging
import mysql.connector
from pathlib import Path
from flask import render_template

html_template_file = 'index.html.template'

latest_batch = None
sql_conn = None
available_batches = dict()
batch_dic = dict()
counter_dict = dict()

def getAllDatesFromDB():
    global latest_batch
    global available_batches
    global sql_conn
    sql_cursor = sql_conn.cursor()
    try:
        sql_cursor.execute("select BATCH from CITY_INFO group by BATCH order by BATCH asc")
        result = sql_cursor.fetchall()
        for row in result:
            latest_batch = row[0]
            available_batches[latest_batch] = ''
        logging.info('got {} batches from DB. latest batch is {}'.format(str(len(available_batches)), latest_batch))
    except Exception as e:
        logging.error('error getting processed dates: {}'.format(e))
    finally:
        sql_cursor.close()


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
        sql_cursor = sql_conn.cursor()
        sql_cursor.execute(
            "select CITY, LAT, LNG, GREEN_COUNT, ORANGE_COUNT, RED_COUNT from CITY_INFO where BATCH = %s ", (batch_id,))
        result = sql_cursor.fetchall()
        for row in result:
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
        counter_dict[latest_batch] = (total_peers, connected_peers, disconnected_peers)
        batch_dic[batch_id] = city_list
        sql_cursor.close()
    return city_list, total_peers, connected_peers, disconnected_peers


def open_sql_conn():
    global sql_conn

    home = str(Path.home())
    db_password_file = home + '/bin/dbpwd'
    file = open(db_password_file, mode='r')
    dbPassword = file.read()
    dbPassword = dbPassword.rstrip('\n')
    file.close()

    ## Open database connection
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
    logging.info('opened database successfully')


if __name__ == "__main__":
    global sql_conn
    global latest_batch

    if sql_conn is None:
        open_sql_conn()
    if latest_batch is None:
        getAllDatesFromDB()

    city_list, total_peers, connected_peers, disconnected_peers = getCityList(latest_batch)
    cols = latest_batch.split('-')
    date_string = cols[0] + '/' + cols[1] + '/' + cols[2] + ' - ' + cols[3] + ' : ' + cols[4]
    html = render_template(html_template_file, city_list=city_list, total_peers=total_peers,
                           connected_peers=connected_peers, disconnected_peers=disconnected_peers,
                           snapshot_time=date_string)
