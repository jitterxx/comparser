#! /bin/bash

HOME_DIR=/home/yurburo
APP_DIR=/home/yurburo/service

cd $APP_DIR/srv &&
$APP_DIR/bin/python ./notificater.py >> $HOME_DIR/email_notify.log


