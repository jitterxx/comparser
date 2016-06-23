#!/usr/bin/python -t
# coding: utf8

import sys
reload(sys)
sys.setdefaultencoding("utf-8")
import mod_classifier_new as clf
import datetime
from configuration import *
import objects as CPO
import sqlalchemy

import uuid


sdate = datetime.datetime.strptime(str("03-03-2015"), "%d-%m-%Y")

edate = datetime.datetime.strptime(str("07-07-2015"), "%d-%m-%Y")

print CPO.pred_stat_get_data(start_date=sdate, end_date=edate)


