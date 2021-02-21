#!/bin/bash

PORT="9786"
CRAWLER_LOGS=/root/logs/crawler.log
CRAWLER="http://45.77.235.53:1635"
DATE=`date '+%Y-%m-%d-%H'`
PWD=`pwd`
DBNAME="$PWD/beenodeslive.db"
HTML_DIR="$PWD/html"

echo "`date` - Starting to process peers"
LIVE_OVERLAYS=`curl -X GET $CRAWLER/topology | jq  | grep -v ":\|}\|]\|{" | tr -d " " | tr -d "\"" | tr -d ","| sort | uniq`
OVERLAY_COUNT=`echo $LIVE_OVERLAYS | wc -l`
echo "`date` - total of $OVERLAY_COUNT overlays to process"

ROWS=$(sqlite3 $DBNAME "select CITY, IP from BEENODES where DATE=\"$DATE\" LIMIT 1;")
if [ $? -eq 1 ]
then
   echo "`date` - ERROR: could not access database"
   exit
fi
if [ ! -z "$ROWS" ]
then
  echo "`date` - ERROR: $DATE is already processed"
  exit
fi


if [ ! -d "$HTML_DIR" ]
then
  mkdir $HTML_DIR
  echo "`date` - created dir $HTML_DIR"
fi


for OVRLA in $LIVE_OVERLAYS
do
   ## Get the IP for the overlay from DB
   IP=$(sqlite3 $DBNAME "select IP from OVERLAYTOIP where OVERLAY=\"$OVRLA\";")
   if [ -z "$IP" ]
   then
      ## If not in the DB, get it from the logs
      IP=$(grep $OVRLA $CRAWLER_LOGS | grep "successfully connected to peer" | grep ip4 | tail -n1 |cut -d "/" -f3)
      if [ ! -z "$IP" ]
      then
         ## insert the harvested IP in to DB for future use
         CMD=$(sqlite3 $DBNAME "insert into OVERLAYTOIP (OVERLAY, IP)  values (\"$OVRLA\",\"$IP\");")
         if [ $? -eq 1 ]
         then
            echo "`date` - ERROR: could not insert $OVRLA and $IP in to OVERLAYTOIP table"
            continue
         else
            echo "`date` - Added $OVRLA and $IP in to OVERLAYTOIP table"
         fi
	    else
	       IP="NOIP"
	       CMD=$(sqlite3 $DBNAME "insert into OVERLAYTOIP (OVERLAY, IP)  values (\"$OVRLA\",\"$IP\");")
	       if [ $? -eq 1 ]
         then
            echo "`date` - ERROR: could not insert $OVRLA and $IP in to OVERLAYTOIP table"
            continue
         else
            echo "`date` - Added $OVRLA and $IP in to OVERLAYTOIP table"
         fi
      fi
   fi

   # if we could not find the IP ignore this overlay, its of no use for us
   if [ "$IP" == "NOIP" ]
   then
     echo "`date` - ERROR: skipping $OVRLA as ip could not be found"
     continue
   fi

   ## Now get the City for the IP
   CITYSTR=$(sqlite3 $DBNAME "select LAT, LNG, CITY from IPTOCITY where IP=\"$IP\";")
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
            echo "`date` - ERROR: could not insert $IP, $LAT, $LNG and $CITY in to IPTOCITY table"
            continue
      else
         echo "`date` - Added $IP, $LAT, $LNG and $CITY in to IPTOCITY table"
      fi
   else
      LAT=$(echo $CITYSTR | cut -d "|" -f1)
      LNG=$(echo $CITYSTR | cut -d "|" -f2)
      CITY=$(echo $CITYSTR | cut -d "|" -f3)
      echo "`date` - Found $IP, $LAT, $LNG and $CITY from IPTOCITY table"
   fi

   ## if city is not there, then ignore this overlay
   if [ "$CITY" == "NOCITY" ]
   then
      echo "`date` - ERROR: could not proceed with $OVRLA as CITY could not be found"
      continue
   fi

   CMD=$(sqlite3 $DBNAME "insert into BEENODES (DATE, CITY, IP)  values (\"$DATE\", \"$CITY\", \"$IP\");")
   if [ $? -eq 1 ]
   then
      echo "`date` - ERROR: could not insert $DATE, $CITY and $IP in to BEENODES table"
      continue
   fi
done

DATE_LOG="$DATE.log"
ROWS=$(sqlite3 $DBNAME "select CITY, COUNT(CITY) from BEENODES where DATE=\"$DATE\" GROUP BY CITY;")
for ROW in $ROWS
do
  CITY=$(echo $ROW | cut -d "|" -f1)
  COUNT=$(echo $ROW | cut -d "|" -f2)
  echo "'$CITY' : [ $LAT, $LNG, $COUNT ]," >> $DATE_LOG
done

## if the datelog file is not created, exit
if [ ! -f "$DATE_LOG" ]; then
    echo "`date` - ERROR: $DATE.log file is not present"
    exit
fi


# create a html using a template
NEW_HTML="$DATE.html"
sed '/CITYMAP/ r $DATE_LOG' index.html.template >> $NEW_HTML
mv $NEW_HTML $HTML_DIR || exit
cd $HTML_DIR || exit
rm index.html || exit
ln -s $NEW_HTML index.html || exit
echo "`date` - Creted new html $NEW_HTML and made it index.html"

# restart the
kill -9 "$(ps -aef | grep http.server | grep -v grep  | tr -s " "  | cut -d " " -f2)" || exit
if [ $? -eq 1 ]
then
    echo "`date` - ERROR: could not kill the python server"
    exit
fi

echo "`date` - Starting python server with new data"
python -m  http.server $PORT &
systemctrl restart nginx


