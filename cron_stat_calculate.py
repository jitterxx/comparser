#!/usr/bin/python -t
# coding: utf8

import sys
reload(sys)
sys.setdefaultencoding("utf-8")

from configuration import *
import objects as CPO
import datetime

__author__ = 'sergey'


# Расчет статистики происходит каждый час
# Рассчитываем за текущий день
# Если время между 00 и 01 часов ночи, пересчитываем прошлый день.


today = datetime.datetime.now()
try:
    print "Рассчитываем день: %s" % today.strftime("%d-%m-%Y %H:%M:%S")
    CPO.pred_stat_compute(for_day=today)
    print "*"*30
except Exception as e:
    print "Ошибка расчета статистики за день %s. " % today
    print str(e)

if today.hour == 0:
    yesterday = today - datetime.timedelta(days=1)
    try:
        print "Рассчитываем вчерашний день: %s" % yesterday.strftime("%d-%m-%Y %H:%M:%S")
        CPO.pred_stat_compute(for_day=yesterday)
        print "*"*30
    except Exception as e:
        print "Ошибка расчета статистики за день %s. " % yesterday
        print str(e)
