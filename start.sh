#!/bin/bash

./stop.sh

# default to one instance
export SEARCH_SERVER_INSTANCES=${SEARCH_SERVER_INSTANCES:-1}

for instance in `seq 1 $SEARCH_SERVER_INSTANCES`; do
  host_port=$(( 9009 + $instance ))
  docker run -p $host_port:9000 --name "search_server_${instance}" -d search_server:latest
done

exit 0
