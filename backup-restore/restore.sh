#!/bin/sh
set -e

echo "Downloading and restoring..."
aws --endpoint-url https://tor1.digitaloceanspaces.com \
  s3 cp s3://finance-tracker/latest.sql.gz - | gunzip | psql -h db -U $PGUSER $DB_NAME

echo "Restore complete"