#!/bin/bash

container_name='search-server'
docker rm $container_name 2>/dev/null
docker run -d -p 9001:8000 --name $container_name $container_name:latest
