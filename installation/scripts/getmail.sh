#! /bin/bash

HOME_DIR=/home/yurburo
APP_DIR=/home/yurburo/service

set -e
cd $HOME_DIR/.getmail
rcfiles=""
for file in getmailrc* ; do
  rcfiles="$rcfiles --rcfile $file"
done
exec /usr/bin/getmail $rcfiles $@

