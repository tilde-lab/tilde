#!/bin/bash

#wget -o /dev/null -q -O /dev/null http://127.0.0.1:8768/?q=$i &
#curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" -H "Host: 127.0.0.1:8768" -H "Origin: http://127.0.0.1:8768" -H "Sec-WebSocket-Version: 13" -H "Sec-WebSocket-Key: 27HryERKvezntsz3wWJa+w==" http://127.0.0.1:8768/websocket &

if [[ $# < 1 ]]; then
    echo "Usage: script #processes"
    exit
fi
start=`date +%H:%M:%S`
for ((i=1; i<=$1; i++))
do
    python $(dirname $0)/gui_client.py &
    echo "Process $i started"
done
wait
end=`date +%H:%M:%S`
echo `hostname` $1 $start $end
