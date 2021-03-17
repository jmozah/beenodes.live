import sys
import mysql.connector

password = sys.argv[1]

mydb = mysql.connector.connect(
  host="localhost",
  user="crawler",
  password=password,
  database="crawler"
)

mycursor = mydb.cursor()
mycursor.execute('''CREATE TABLE PEER_INFO (
          OVERLAY      VARCHAR(64)    NOT NULL,
          IP4or6       VARCHAR(10)     NOT NULL,
          IP           VARCHAR(50)    NOT NULL,
          PROTOCOL     VARCHAR(10)    NOT NULL,
          PORT         MEDIUMINT      NOT NULL,
          UNDERLAY     VARCHAR(64)    NOT NULL,
          CONNECTED    BOOLEAN        NOT NULL,
          RETRY_COUNT  MEDIUMINT      NOT NULL,
          PEERS_COUNT  MEDIUMINT      NOT NULL,
          Timestamp    DATETIME       DEFAULT  CURRENT_TIMESTAMP,
          PRIMARY KEY(OVERLAY));''')

mycursor.execute(''' CREATE TABLE NEIGHBOUR_INFO (
          BASE_OVERLAY         VARCHAR(64)     NOT NULL,
          PROXIMITY_ORDER      TINYINT         NOT NULL,
          NEIGHBOUR_OVERLAY    VARCHAR(64)     NOT NULL,
          Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY(BASE_OVERLAY, NEIGHBOUR_OVERLAY));''')

mycursor.execute('''CREATE TABLE IP_INFO
         (IP             VARCHAR(20)      PRIMARY KEY,
          LAT            FLOAT            NOT NULL,
          LNG            FLOAT            NOT NULL,
          CITY           VARCHAR(100)     NOT NULL,
          COUNTRY        VARCHAR(100)     NOT NULL,
          ASN            VARCHAR(20)      NOT NULL,
          ORGANISATION   VARCHAR(200)     NOT NULL,
          TYPE           VARCHAR(20)      NOT NULL, 
          Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP);''')
mycursor.execute('''CREATE INDEX IP_info_CITY on IP_INFO(CITY)''')
mycursor.execute('''CREATE INDEX IP_info_COUNTRY on IP_INFO(COUNTRY)''')
mycursor.execute('''CREATE INDEX IP_info_ORGANISATION on IP_INFO(ORGANISATION)''')
mycursor.execute('''CREATE INDEX IP_info_TYPE on IP_INFO(TYPE)''')

mycursor.execute('''CREATE TABLE CITY_INFO (
          BATCH           VARCHAR(20)    NOT NULL,
          CITY            VARCHAR(100)   NOT NULL,
          LAT             FLOAT          NOT NULL,
          LNG             FLOAT          NOT NULL,
          GREEN_COUNT     INT            NOT NULL,
          ORANGE_COUNT    INT            NOT NULL,
          RED_COUNT       INT            NOT NULL,
          Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY(BATCH, CITY));''')
mycursor.execute('''CREATE INDEX city_info_batch on CITY_INFO(BATCH)''')
mycursor.close()


