#! /bin/bash

HOME_DIR=/home/yurburo
APP_DIR=/home/yurburo/service

$APP_DIR/bin/python $APP_DIR/srv/cron_stat_calculate.py >> $HOME_DIR/statistics.log


