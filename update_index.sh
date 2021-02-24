#!/bin/bash

echo "$(date) - starting update_index with pid $$"
RUNNING=$(ps -aef | grep update_index | grep -v grep )
if [ ! -z "$RUNNING" ]
then
  echo "$(date) - update script is already running..."
  exit
fi

BEENODES_HOME="/root/beenodes.live"
cd $BEENODES_HOME || exit

PORT="9786"
CRAWLER_LOGS=/root/logs/crawler.log
CRAWLER="http://localhost:1635"
DATE=$(date '+%Y-%m-%d-%H')
PWD=`pwd`
DBNAME="$PWD/beenodeslive.db"
HTML_DIR="$PWD/html"

echo "$(date) - Starting to process peers"
LIVE_OVERLAYS=`curl -X GET $CRAWLER/topology | jq  | grep -v ":\|}\|]\|{" | tr -d " " | tr -d "\"" | tr -d ","| sort | uniq`
OVERLAY_COUNT=`echo $LIVE_OVERLAYS | wc -l`
echo "$(date) - total of $OVERLAY_COUNT overlays to process"

if [ ! -d "$HTML_DIR" ]
then
  mkdir $HTML_DIR
  echo "$(date) - created dir $HTML_DIR"
fi

TOTAL_OVERLAYS=0
NEW_OVERLAYS=0
NEW_IPS=0
NEW_CITIS=0
TOTAL_NODES=0

ERR_INSERTING_IP=0
ERR_INSERTING_NOIP=0
ERR_NOIP=0
ERR_INSERTING_CITY=0
ERR_NOCITY=0
ERR_INSERTING_BEENODES=0
ERR_NO_DATELOG=0
ERR_NO_DB=0


AddCountersToDB () {
  CMD=$(sqlite3 $DBNAME "insert into COUNTERS (TOTAL_OVERLAYS, NEW_OVERLAYS, NEW_IPS, NEW_CITIS, TOTAL_NODES, ERR_INSERTING_IP, ERR_INSERTING_NOIP, ERR_NOIP, ERR_INSERTING_CITY, ERR_NOCITY, ERR_INSERTING_BEENODES, ERR_NO_DATELOG, ERR_NO_DB)  values (\"$TOTAL_OVERLAYS\",\"$NEW_OVERLAYS\",\"$NEW_IPS\",\"$NEW_CITIS\",\"$TOTAL_NODES\",\"$ERR_INSERTING_IP\",\"$ERR_INSERTING_NOIP\",\"$ERR_NOIP\",\"$ERR_INSERTING_CITY\",\"$ERR_NOCITY\",\"$ERR_INSERTING_BEENODES\",\"$ERR_NO_DATELOG\",\"$ERR_NO_DB\");")
}


CRAWLER_OVERLAY=$(curl -X GET http://localhost:1635/topology | jq  '.baseAddr' | tr -d "\"")
ROWS=$(sqlite3 $DBNAME "select * from BEENODES where DATE=\"$DATE\" LIMIT 1;")
if [ $? -eq 1 ]
then
   ERR_NO_DB=$((ERR_NO_DB+1))
   echo "$(date) - ERROR: could not access database"
   AddCountersToDB
   exit
fi

if [ ! -z "$ROWS" ]
then
   echo "$(date) - $DATE is already processed, just updating the html file"
else
   for OVRLA in $LIVE_OVERLAYS
   do
   TOTAL_OVERLAYS=$((TOTAL_OVERLAYS+1))
   if [ "$OVRLA" == "$CRAWLER_OVERLAY" ]
   then
      echo "Ignoring crawler overlay $OVRLA"
      continue
   fi

   ## Get the IP for the overlay from DB
   IP=$(sqlite3 $DBNAME "select IP from OVERLAYTOIP where OVERLAY=\"$OVRLA\";")
   if [ -z "$IP" ]
   then
      NEW_OVERLAYS=$((NEW_OVERLAYS+1))

      ## If not in the DB or has "NOIP", check the logs to see if we can harvest the ip from there
      IP=$(grep $OVRLA $CRAWLER_LOGS | grep "successfully connected to peer\|peer not reachable from kademlia" | grep ip4 | tail -n1 |cut -d "/" -f3)
      if [ ! -z "$IP" ]
      then
         if [ "$IP" == "127.0.0.1" ]
         then
            continue
         fi

         ## insert the harvested IP in to DB for future use
         CMD=$(sqlite3 $DBNAME "insert into OVERLAYTOIP (OVERLAY, IP)  values (\"$OVRLA\",\"$IP\");")
         if [ $? -eq 1 ]
         then
            ERR_INSERTING_IP=$((ERR_INSERTING_IP+1))
            echo "$(date) - ERROR: could not insert $OVRLA and $IP in to OVERLAYTOIP table"
            continue
         else
            NEW_IPS=$((NEW_IPS+1))
            echo "$(date) - Added $OVRLA and $IP in to OVERLAYTOIP table"
         fi
      else
         # if we could not find the IP ignore this overlay, its of no use for us
         ERR_NOIP=$((ERR_NOIP+1))
         echo "$(date) - ERROR: skipping $OVRLA as ip could not be found"
         continue
      fi
   fi


   ## Now get the City for the IP
   CITYSTR=$(sqlite3 $DBNAME "select ID, LAT, LNG, CITY from IPTOCITY where IP=\"$IP\";")
   if [ -z "$CITYSTR" ]
   then
      url=$(curl -X GET "http://ipinfo.io/${IP}?token=21a1a8a7be196b")
      CITY=$(echo $url | jq -r '.city')
      if [ -z "$CITY" ]
      then
         CITY="NOCITY"
      fi
      loc=$(echo $url | jq -r '.loc')
      LAT=$(echo $loc |cut -d "," -f1)
      LNG=$(echo $loc |cut -d "," -f2)
      CMD=$(sqlite3 $DBNAME "insert into IPTOCITY (IP, LAT, LNG, CITY)  values (\"$IP\", \"$LAT\", \"$LNG\", \"$CITY\");")
      if [ $? -eq 1 ]
         then
            ERR_INSERTING_CITY=$((ERR_INSERTING_CITY+1))
            echo "$(date) - ERROR: could not insert $IP, $LAT, $LNG and $CITY in to IPTOCITY table"
            continue
      else
         NEW_CITIS=$((NEW_CITIS+1))
         echo "$(date) - Added $IP, $LAT, $LNG and $CITY in to IPTOCITY table"
      fi
      ID=$(sqlite3 $DBNAME "select MAX(ID) from IPTOCITY;")
   else
      ID=$(echo $CITYSTR | cut -d "|" -f1)
      LAT=$(echo $CITYSTR | cut -d "|" -f2)
      LNG=$(echo $CITYSTR | cut -d "|" -f3)
      CITY=$(echo $CITYSTR | cut -d "|" -f4)
      echo "$(date) - Found $IP, $LAT, $LNG and $CITY from IPTOCITY table"
   fi

   ## if city is not there, then ignore this overlay
   if [ "$CITY" == "NOCITY" ]
   then
      ERR_NOCITY=$((ERR_NOCITY+1))
      echo "$(date) - ERROR: could not proceed with $OVRLA as CITY could not be found"
      continue
   fi

   CMD=$(sqlite3 $DBNAME "insert into BEENODES (DATE, IPTOCITY_ID)  values (\"$DATE\", \"$ID\");")
   if [ $? -eq 1 ]
   then
      ERR_INSERTING_BEENODES=$((ERR_INSERTING_BEENODES+1))
      echo "$(date) - ERROR: could not insert $DATE and $ID in to BEENODES table"
      continue
   fi
   TOTAL_NODES=$((TOTAL_NODES+1))
done
fi

DATE_LOG="$PWD/log/$DATE.log"
ROWS_FILE="$PWD/log/rows.log"
rm $ROWS_FILE
rm $DATE_LOG
CMD=$(sqlite3 "$DBNAME" "select CITY, LAT, LNG, COUNT(CITY) from BEENODES INNER JOIN IPTOCITY on IPTOCITY.ID = BEENODES.IPTOCITY_ID where DATE=\"$DATE\" GROUP BY CITY;")
echo "$CMD" >> $ROWS_FILE
ROWS=`cat $ROWS_FILE`
cat $ROWS_FILE | while read LINE
do
  CITY=$(echo $LINE | cut -d "|" -f1)
  LAT=$(echo $LINE | cut -d "|" -f2)
  LNG=$(echo $LINE | cut -d "|" -f3)
  COUNT=$(echo $LINE | cut -d "|" -f4)
  if [ "$CITY" == "null" ]
  then
      continue
  fi
  echo "'$CITY' : [ $LAT, $LNG, $COUNT ]," >> $DATE_LOG
done

## if the datelog file is not created, exit
if [ ! -f "$DATE_LOG" ]; then
    ERR_NO_DATELOG=$((ERR_NO_DATELOG+1))
    AddCountersToDB
    echo "$(date) - ERROR: $DATE.log file is not present"
    exit
fi

AddCountersToDB

# create a html using a template
NEW_HTML="$DATE.html"
SED="sed '/CITYMAP/r $DATE_LOG' index.html.template"
echo $SED | sh - >> $NEW_HTML
mv $NEW_HTML $HTML_DIR || exit
cd $HTML_DIR || exit
rm index.html || exit
ln -s $NEW_HTML index.html || exit
echo "$(date) - Creted new html $NEW_HTML and made it index.html"

# restart the webserver
kill -9 "$(ps -aef | grep http.server | grep -v grep  | tr -s " "  | cut -d " " -f2)"
echo "$(date) - Starting python server with new html file $NEW_HTML"
python3 -m  http.server $PORT >> /root/beenodes.log 2>&1 &
systemctl restart nginx
echo "$(date) - ending update_index with pid $$"

