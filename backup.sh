#!/bin/sh

set -e

echo "Installing dependencies..."
apt-get update && apt-get install -y awscli gzip

TIMESTAMP=$(date +%F-%H-%M)
FILE="/tmp/backup.sql.gz"

echo "Dumping DB..."
pg_dump -h db -U $PGUSER $DB_NAME | gzip > $FILE

echo "Uploading to Spaces..."
aws --endpoint-url https://tor1.digitaloceanspaces.com \
  s3 cp $FILE s3://finance-tracker/backup-$TIMESTAMP.sql.gz

aws --endpoint-url https://tor1.digitaloceanspaces.com \
  s3 cp $FILE s3://finance-tracker/latest.sql.gz

echo "Backup complete"