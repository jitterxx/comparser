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


date = datetime.datetime.strptime(str("04-04-2016"), "%d-%m-%Y")

CPO.create_tables()

CPO.CURRENT_TRAIN_EPOCH = 2

print CPO.CURRENT_TRAIN_EPOCH

CPO.pred_stat_compute(for_day=date)


