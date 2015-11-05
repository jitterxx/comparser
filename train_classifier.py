#!/usr/bin/python -t
# coding: utf8

"""
Фильтрация и классификация текстов(документов), сообщений и т.д.

"""
from operator import itemgetter
import re
import argparse
import mod_classifier as cl
import mysql.connector
import math
from configuration import *
import sys
reload(sys)
sys.setdefaultencoding("utf-8")



# Создаем объект классификатора
f_cl = cl.fisherclassifier(cl.specfeatures)

# Подключаем данные обучения
f_cl.setdb("classifier")


f_cl.loaddb()
cat = f_cl.category_code
minimums = f_cl.minimums

for i in cat.keys():
    print "Категория: ", cat[i], "(", i, ") : ", minimums[i]

# Обучаем модель на тестовых данных из базы
f_cl.sql_train()

# Закрываем соединение с БД
f_cl.unsetdb()






