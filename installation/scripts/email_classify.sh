#! /bin/bash

HOME_DIR=/home/yurburo
APP_DIR=/home/yurburo/service

$APP_DIR/bin/python $APP_DIR/srv/email_classify_new.py -d -l 50 >> $HOME_DIR/email_classify.log


