#!/bin/bash

CRAWLER_LOGS=/root/logs/crawler.log
LIVE_OVERLAYS=`curl -X GET http://localhost:1635/topology | jq  | grep -v ":\|}\|]\|{" | tr -d " " | tr -d "\"" | tr -d ","| sort | uniq`
DATE=`date '+%Y-%m-%d-%H'`

for OVRLA in $LIVE_OVERLAYS
do
   IP=`sqlite3 beenodeslive.db "select IP from OVERLAYTOIP where OVERLAY=$OVRLA;"`
   if [ -z "$IP" ]
   then	   
      IP=`grep $OVRLA $CRAWLER_LOGS | grep "successfully connected to peer" | grep "successfully connected to peer" | grep ip4 | tail -n1 |cut -d "/" -f3`
      if [ ! -z "$IP" ]
      then	   
	 echo "going to insert"     
         CMD=`sqlite3 beenodeslive.db "insert into OVERLAYTOIP (OVERLAY, IP)  values (\"$OVRLA\",\"$IP\");"`
	 if [ $CMD ]
	 then
           echo "Added $OVRLA $IP to db"
	 fi	 
      fi    
   else
      echo "Got $OVRLA $IP from db"
   fi
done	


