#! /bin/bash

HOME_DIR=/home/yurburo
APP_DIR=/home/yurburo/service

$APP_DIR/bin/python $APP_DIR/srv/email_parse.py -d -l 1000 >> $HOME_DIR/email_parse.log

