#!/usr/bin/python -t
# coding: utf8

import sys
reload(sys)
sys.setdefaultencoding("utf-8")
sys.path.extend(['/Users/sergey/PycharmProjects/comparser/'])

import datetime
from configuration import *
import objects as CPO


import uuid

# CPO.pred_stat_compute(for_day=datetime.datetime.strptime(str("01-06-2016"), "%d-%m-%Y"))

sdate = datetime.datetime.strptime(str("31-05-2016"), "%d-%m-%Y")

edate = datetime.datetime.strptime(str("04-06-2016"), "%d-%m-%Y")

stat = CPO.pred_stat_get_data_agr(start_date=sdate, end_date=edate)

print stat




