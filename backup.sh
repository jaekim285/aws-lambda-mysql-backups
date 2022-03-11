#!/usr/bin/env bash

HOST=$1
USERNAME=$2
PASSWORD=$3
DB=$4

export MYSQL_PWD="${PASSWORD}"

/tmp/mysqldump -v --host ${HOST} --user ${USERNAME} --max_allowed_packet=1G --single-transaction --quick \
    --lock-tables=false --routines ${DB} > /tmp/backup.sql