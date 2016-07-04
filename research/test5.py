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

#print CPO.pred_stat_compute(for_day=datetime.datetime.strptime("09-06-2016", "%d-%m-%Y"))
print CPO.pred_stat_get_data_agr(start_date=datetime.datetime.strptime("01-01-2016", "%d-%m-%Y"),
                                 end_date=datetime.datetime.now())



