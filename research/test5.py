#!/usr/bin/python -t
# coding: utf8

import sys
reload(sys)
sys.setdefaultencoding("utf-8")
sys.path.extend(['..'])

import datetime
from configuration import *
import objects as CPO


import uuid

#print CPO.pred_stat_compute(for_day=datetime.datetime.strptime("09-06-2016", "%d-%m-%Y"))

#CPO.create_tables()

CPO.get_stat_for_management(start=datetime.datetime.strptime("18-07-2016", "%d-%m-%Y"),
                            end=datetime.datetime.strptime("22-07-2016", "%d-%m-%Y"))

