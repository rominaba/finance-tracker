#!/bin/sh

echo "Running migrations..."
flask db upgrade

sleep 3

echo "Starting Flask server..."
flask run --host=0.0.0.0 --port=5000