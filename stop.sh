#!/bin/bash

export SEARCH_SERVER_INSTANCES=${SEARCH_SERVER_INSTANCES:-1}

for instance in `seq 1 $SEARCH_SERVER_INSTANCES`; do
  # stop the server
  docker stop "search_server_${instance}"
done

exit 0
