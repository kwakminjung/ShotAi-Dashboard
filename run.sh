#!/bin/bash

IMAGE_NAME="shotai-dashboard-app"
CONTAINER_NAME="shotai-dashboard-container"

PORT=${1:-8000}

docker stop $CONTAINER_NAME 2>/dev/null
docker rm $CONTAINER_NAME 2>/dev/null

docker build -t $IMAGE_NAME .

docker run --rm --network host \
--name $CONTAINER_NAME $IMAGE_NAME \
--host 0.0.0.0 --port $PORT