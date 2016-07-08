#!/usr/bin/python -t
# coding: utf8

import sys
reload(sys)
sys.setdefaultencoding("utf-8")
sys.path.extend(['~/dev/conflict analyser/'])

import datetime
from configuration import *
import objects as CPO


import uuid

#print CPO.pred_stat_compute(for_day=datetime.datetime.strptime("09-06-2016", "%d-%m-%Y"))


# CPO.add_warn_task_stat(for_day=datetime.datetime.strptime("11-03-2016", "%d-%m-%Y"))

CPO.show_warn_task_stat(start=datetime.datetime.strptime("03-03-2016", "%d-%m-%Y"),
                        end=datetime.datetime.strptime("10-03-2016", "%d-%m-%Y"))
